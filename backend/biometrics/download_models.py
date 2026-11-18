from pathlib import Path
import hashlib
import sys
import urllib.error
import urllib.request

import cv2


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model_assets"
MODEL_ASSETS = {
    "face_detection_yunet_2023mar.onnx": {
        "urls": [
            "https://huggingface.co/pollen-robotics/face_detection_yunet_2023mar/resolve/main/face_detection_yunet_2023mar.onnx",
            "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
            "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        ],
        "minimum_bytes": 200_000,
        "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    },
    "face_recognition_sface_2021dec.onnx": {
        "urls": [
            "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
            "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
            "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        ],
        "minimum_bytes": 30_000_000,
        "sha256": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    },
}
LICENSE_ASSETS = {
    "LICENSE_YUNET.txt": {
        "urls": [
            "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_detection_yunet/LICENSE",
            "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/LICENSE",
        ],
        "minimum_bytes": 500,
    },
    "LICENSE_SFACE.txt": {
        "urls": [
            "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_recognition_sface/LICENSE",
            "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE",
        ],
        "minimum_bytes": 1000,
    },
}


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(filename, details):
    destination = MODEL_DIR / filename
    if (
        destination.is_file()
        and destination.stat().st_size >= details["minimum_bytes"]
        and _sha256(destination) == details["sha256"]
    ):
        return destination

    errors = []
    for url in details["urls"]:
        temporary = destination.with_suffix(destination.suffix + ".download")
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "RollNexa-model-installer/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            if temporary.stat().st_size < details["minimum_bytes"]:
                raise RuntimeError("The downloaded file is smaller than the expected model size.")
            if _sha256(temporary) != details["sha256"]:
                raise RuntimeError("The downloaded model failed its SHA-256 integrity check.")
            temporary.replace(destination)
            return destination
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            errors.append(f"{url}: {exc}")
            temporary.unlink(missing_ok=True)

    raise RuntimeError(f"Could not download {filename}. " + " | ".join(errors))


def download_license(filename, details):
    destination = MODEL_DIR / filename
    if destination.is_file() and destination.stat().st_size >= details["minimum_bytes"]:
        return destination
    errors = []
    for url in details["urls"]:
        temporary = destination.with_suffix(destination.suffix + ".download")
        request = urllib.request.Request(url, headers={"User-Agent": "RollNexa-model-installer/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as output:
                output.write(response.read())
            if temporary.stat().st_size < details["minimum_bytes"]:
                raise RuntimeError("The downloaded licence notice is incomplete.")
            temporary.replace(destination)
            return destination
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            errors.append(f"{url}: {exc}")
            temporary.unlink(missing_ok=True)
    raise RuntimeError(f"Could not download {filename}. " + " | ".join(errors))


def validate_models():
    detector_path = str(MODEL_DIR / "face_detection_yunet_2023mar.onnx")
    recognizer_path = str(MODEL_DIR / "face_recognition_sface_2021dec.onnx")
    detector = cv2.FaceDetectorYN.create(detector_path, "", (320, 320), 0.75, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
    if detector is None or recognizer is None:
        raise RuntimeError("OpenCV could not initialise the facial recognition models.")


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for filename, details in MODEL_ASSETS.items():
        path = download_asset(filename, details)
        print(f"Installed {filename} ({path.stat().st_size} bytes)")
    for filename, details in LICENSE_ASSETS.items():
        path = download_license(filename, details)
        print(f"Installed {filename} ({path.stat().st_size} bytes)")
    validate_models()
    print("Facial recognition model assets validated successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Facial model installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
