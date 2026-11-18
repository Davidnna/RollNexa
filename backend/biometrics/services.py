from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import threading

import cv2
import numpy as np
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


MODEL_VERSION = "opencv-yunet-2023mar+sface-2021dec"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 4_000_000
MIN_IMAGE_WIDTH = 320
MIN_IMAGE_HEIGHT = 240
MIN_FACE_EDGE = 80
DEFAULT_FACE_DETECTION_THRESHOLD = 0.75
MIN_YAW_CHANGE = 0.08

_INFERENCE_LOCK = threading.Lock()
cv2.setNumThreads(1)


class BiometricServiceError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class BiometricServiceUnavailable(BiometricServiceError):
    pass


@dataclass
class FaceSample:
    embedding: np.ndarray
    yaw_ratio: float


def _fernet():
    key = getattr(settings, "BIOMETRIC_ENCRYPTION_KEY", "")
    if isinstance(key, bytes):
        key_bytes = key.strip()
    elif isinstance(key, str):
        key = key.strip()
        if not key:
            raise BiometricServiceUnavailable(
                "encryption_key_missing",
                "Biometric verification is not configured. Contact the system administrator.",
            )
        try:
            key_bytes = key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise BiometricServiceUnavailable(
                "encryption_key_invalid",
                "The biometric encryption key is invalid. Contact the system administrator.",
            ) from exc
    else:
        key_bytes = b""

    if not key_bytes:
        raise BiometricServiceUnavailable(
            "encryption_key_missing",
            "Biometric verification is not configured. Contact the system administrator.",
        )

    # Accept an omitted Base64 padding character while retaining Fernet's
    # required 32-byte decoded key length. Never derive or silently replace keys.
    key_bytes += b"=" * (-len(key_bytes) % 4)
    try:
        return Fernet(key_bytes)
    except (TypeError, ValueError) as exc:
        raise BiometricServiceUnavailable(
            "encryption_key_invalid",
            "The biometric encryption key is invalid. Contact the system administrator.",
        ) from exc


def biometric_encryption_key_status():
    """Return non-secret key configuration status for the student settings UI."""
    key = getattr(settings, "BIOMETRIC_ENCRYPTION_KEY", "")
    if not key or (isinstance(key, str) and not key.strip()):
        return "missing"
    try:
        _fernet()
    except BiometricServiceUnavailable as exc:
        return "invalid" if exc.code == "encryption_key_invalid" else "missing"
    return "valid"


def encrypt_template(embedding):
    vector = _normalise_embedding(embedding)
    return _fernet().encrypt(vector.astype("<f4").tobytes())


def decrypt_template(encrypted_template):
    try:
        raw = _fernet().decrypt(bytes(encrypted_template))
    except InvalidToken as exc:
        raise BiometricServiceUnavailable(
            "template_decryption_failed",
            "The stored facial template could not be decrypted. Contact the system administrator.",
        ) from exc
    vector = np.frombuffer(raw, dtype="<f4")
    if vector.shape != (128,):
        raise BiometricServiceUnavailable(
            "template_format_invalid",
            "The stored facial template has an unsupported format. Re-enrolment is required.",
        )
    return _normalise_embedding(vector)


def _normalise_embedding(embedding):
    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if vector.shape != (128,):
        raise BiometricServiceError("embedding_invalid", "The facial model returned an invalid feature vector.")
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0:
        raise BiometricServiceError("embedding_invalid", "The facial model returned an invalid feature vector.")
    return vector / norm


@lru_cache(maxsize=2)
def _load_models(model_directory, score_threshold):
    model_dir = Path(model_directory)
    detector_path = model_dir / "face_detection_yunet_2023mar.onnx"
    recognizer_path = model_dir / "face_recognition_sface_2021dec.onnx"
    if not detector_path.is_file() or not recognizer_path.is_file():
        raise BiometricServiceUnavailable(
            "models_missing",
            "Facial recognition models are not installed on this server. Contact the system administrator.",
        )
    try:
        detector = cv2.FaceDetectorYN.create(
            str(detector_path),
            "",
            (320, 320),
            score_threshold,
            0.3,
            5000,
        )
        recognizer = cv2.FaceRecognizerSF.create(str(recognizer_path), "")
    except cv2.error as exc:
        raise BiometricServiceUnavailable(
            "models_unavailable",
            "Facial recognition models could not be loaded. Contact the system administrator.",
        ) from exc
    return detector, recognizer


def _decode_image(uploaded_file):
    if uploaded_file is None:
        raise BiometricServiceError("image_missing", "A camera frame is required.")
    if getattr(uploaded_file, "size", 0) > MAX_IMAGE_BYTES:
        raise BiometricServiceError("image_too_large", "Each camera frame must be no larger than 2 MB.")
    raw = uploaded_file.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise BiometricServiceError("image_too_large", "Each camera frame must be no larger than 2 MB.")
    if not raw:
        raise BiometricServiceError("image_empty", "The camera frame is empty. Capture the image again.")

    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise BiometricServiceError("image_invalid", "The uploaded camera frame is not a supported image.")
    height, width = image.shape[:2]
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise BiometricServiceError(
            "image_resolution_low",
            "The camera frame is too small. Use a camera resolution of at least 320 by 240 pixels.",
        )
    if width * height > MAX_IMAGE_PIXELS:
        raise BiometricServiceError("image_resolution_high", "The camera frame resolution is too large.")
    return image


def _face_detection_threshold():
    return float(getattr(settings, "BIOMETRIC_FACE_DETECTION_THRESHOLD", DEFAULT_FACE_DETECTION_THRESHOLD))


def _face_yaw_ratio(face):
    eye_one_x = float(face[4])
    eye_two_x = float(face[6])
    nose_x = float(face[8])
    eye_distance = abs(eye_two_x - eye_one_x)
    if eye_distance < 20:
        raise BiometricServiceError("face_pose_invalid", "Keep both eyes visible and face the camera.")
    return (nose_x - min(eye_one_x, eye_two_x)) / eye_distance


def inspect_face_frame(uploaded_file):
    """Inspect one transient camera frame and return safe live-position feedback."""
    image = _decode_image(uploaded_file)
    height, width = image.shape[:2]
    threshold = _face_detection_threshold()
    try:
        with _INFERENCE_LOCK:
            detector, _ = _load_models(str(getattr(settings, "BIOMETRIC_MODEL_DIR")), threshold)
            detector.setInputSize((width, height))
            _, faces = detector.detect(image)
    except cv2.error as exc:
        raise BiometricServiceUnavailable(
            "model_inference_failed",
            "Live face detection could not process this camera frame. Restart the camera or try again.",
        ) from exc

    if faces is None or len(faces) == 0:
        return {
            "status": "no_face",
            "ready": False,
            "faceCount": 0,
            "message": "No face detected yet. Move into the frame and face the camera.",
            "boundingBox": None,
            "poseRatio": None,
        }
    if len(faces) != 1:
        return {
            "status": "multiple_faces",
            "ready": False,
            "faceCount": int(len(faces)),
            "message": "Only one person should be visible. Ask others to move out of the camera view.",
            "boundingBox": None,
            "poseRatio": None,
        }

    face = faces[0]
    x, y, face_width, face_height = (float(face[index]) for index in range(4))
    if float(face[14]) < threshold:
        return {
            "status": "unclear_face",
            "ready": False,
            "faceCount": 1,
            "message": "The face is not clear enough yet. Improve the light in front of you and hold still.",
            "boundingBox": None,
            "poseRatio": None,
        }
    if face_width < MIN_FACE_EDGE or face_height < MIN_FACE_EDGE:
        return {
            "status": "move_closer",
            "ready": False,
            "faceCount": 1,
            "message": "Move a little closer so your face is larger in the frame.",
            "boundingBox": None,
            "poseRatio": None,
        }

    normalized_width = face_width / width
    normalized_height = face_height / height
    center_x = (x + face_width / 2) / width
    center_y = (y + face_height / 2) / height
    bounding_box = {
        "x": max(0.0, min(1.0, x / width)),
        "y": max(0.0, min(1.0, y / height)),
        "width": max(0.0, min(1.0, face_width / width)),
        "height": max(0.0, min(1.0, face_height / height)),
    }

    if normalized_width > 0.72 or normalized_height > 0.86:
        return {
            "status": "move_back",
            "ready": False,
            "faceCount": 1,
            "message": "Move slightly farther from the camera so your full face fits inside the guide.",
            "boundingBox": bounding_box,
            "poseRatio": None,
        }
    if normalized_width < 0.16 or normalized_height < 0.24:
        return {
            "status": "move_closer",
            "ready": False,
            "faceCount": 1,
            "message": "Move a little closer so your face is larger in the frame.",
            "boundingBox": bounding_box,
            "poseRatio": None,
        }
    if not (0.30 <= center_x <= 0.70 and 0.18 <= center_y <= 0.82):
        return {
            "status": "centre_face",
            "ready": False,
            "faceCount": 1,
            "message": "Move your face into the centre of the guide.",
            "boundingBox": bounding_box,
            "poseRatio": None,
        }

    try:
        pose_ratio = _face_yaw_ratio(face)
    except BiometricServiceError:
        return {
            "status": "face_pose_invalid",
            "ready": False,
            "faceCount": 1,
            "message": "Keep both eyes visible and face the camera.",
            "boundingBox": bounding_box,
            "poseRatio": None,
        }

    return {
        "status": "face_ready",
        "ready": True,
        "faceCount": 1,
        "message": "Face detected. Hold this position.",
        "boundingBox": bounding_box,
        "poseRatio": float(pose_ratio),
    }


def _extract_face_sample(uploaded_file):
    image = _decode_image(uploaded_file)
    height, width = image.shape[:2]
    threshold = _face_detection_threshold()
    try:
        with _INFERENCE_LOCK:
            detector, recognizer = _load_models(str(getattr(settings, "BIOMETRIC_MODEL_DIR")), threshold)
            detector.setInputSize((width, height))
            _, faces = detector.detect(image)
            if faces is None or len(faces) == 0:
                raise BiometricServiceError(
                    "face_not_found",
                    "No face was detected in this capture. Use the live guide to position your face, then try again.",
                )
            if len(faces) != 1:
                raise BiometricServiceError("multiple_faces", "Only one face may appear in the camera frame.")

            face = faces[0]
            if float(face[14]) < threshold:
                raise BiometricServiceError("face_quality_low", "The face image is unclear. Improve the light and hold still.")
            if float(face[2]) < MIN_FACE_EDGE or float(face[3]) < MIN_FACE_EDGE:
                raise BiometricServiceError("face_too_small", "Move closer to the camera so your face is clearly visible.")

            yaw_ratio = _face_yaw_ratio(face)
            aligned = recognizer.alignCrop(image, face)
            feature = recognizer.feature(aligned)
            embedding = _normalise_embedding(feature)
    except cv2.error as exc:
        raise BiometricServiceUnavailable(
            "model_inference_failed",
            "Facial recognition could not process this image. Try again or contact the system administrator.",
        ) from exc
    return FaceSample(embedding=embedding, yaw_ratio=yaw_ratio)


def _similarity(left, right):
    return float(np.dot(_normalise_embedding(left), _normalise_embedding(right)))


def build_enrollment_template(frames):
    if len(frames) != 3:
        raise BiometricServiceError("enrollment_frame_count", "Capture exactly three facial enrolment frames.")
    samples = [_extract_face_sample(frame) for frame in frames]
    threshold = float(getattr(settings, "BIOMETRIC_FACE_MATCH_THRESHOLD", 0.363))
    if samples[1].yaw_ratio > samples[0].yaw_ratio - MIN_YAW_CHANGE:
        raise BiometricServiceError(
            "enrollment_left_pose_missing",
            "The second enrolment frame must show a slight turn toward the left side of the screen.",
        )
    if samples[2].yaw_ratio < samples[0].yaw_ratio + MIN_YAW_CHANGE:
        raise BiometricServiceError(
            "enrollment_right_pose_missing",
            "The third enrolment frame must show a slight turn toward the right side of the screen.",
        )
    for index, sample in enumerate(samples):
        for other in samples[index + 1:]:
            if _similarity(sample.embedding, other.embedding) < threshold:
                raise BiometricServiceError(
                    "enrollment_identity_inconsistent",
                    "The three captures do not appear to show the same person. Retake the enrolment frames in good lighting.",
                )
    average = np.mean(np.stack([sample.embedding for sample in samples]), axis=0)
    return _normalise_embedding(average)


def verify_face_challenge(*, baseline_frame, challenge_frame, encrypted_template, direction):
    baseline = _extract_face_sample(baseline_frame)
    challenged = _extract_face_sample(challenge_frame)
    template = decrypt_template(encrypted_template)
    threshold = float(getattr(settings, "BIOMETRIC_FACE_MATCH_THRESHOLD", 0.363))

    baseline_score = _similarity(baseline.embedding, template)
    challenge_score = _similarity(challenged.embedding, template)
    pair_score = _similarity(baseline.embedding, challenged.embedding)
    if min(baseline_score, challenge_score, pair_score) < threshold:
        raise BiometricServiceError(
            "face_mismatch",
            "Your face could not be matched to the enrolled student profile. Adjust your position and try again.",
        )

    yaw_change = challenged.yaw_ratio - baseline.yaw_ratio
    if direction == "turn_left":
        liveness_passed = yaw_change <= -MIN_YAW_CHANGE
    elif direction == "turn_right":
        liveness_passed = yaw_change >= MIN_YAW_CHANGE
    else:
        raise BiometricServiceError("challenge_invalid", "The facial verification challenge is invalid. Start again.")

    if not liveness_passed:
        raise BiometricServiceError(
            "liveness_failed",
            "The requested head movement was not detected. Follow the instruction and capture the second frame again.",
        )
    return {
        "liveness_passed": True,
        "model_version": MODEL_VERSION,
    }


def biometric_models_available():
    model_dir = Path(getattr(settings, "BIOMETRIC_MODEL_DIR"))
    return (
        (model_dir / "face_detection_yunet_2023mar.onnx").is_file()
        and (model_dir / "face_recognition_sface_2021dec.onnx").is_file()
    )
