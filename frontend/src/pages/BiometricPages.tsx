import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, Camera, CheckCircle2, LoaderCircle, ShieldCheck, Trash2 } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";

interface BiometricStatus {
    consentStatus: "not_given" | "granted" | "withdrawn" | "consent_update_required";
    consentPolicyVersion: string | null;
    currentPolicyVersion: string;
    consentGrantedAt: string | null;
    consentWithdrawnAt: string | null;
    isEnrolled: boolean;
    enrolledAt: string | null;
    modelVersion: string | null;
    modelsAvailable: boolean;
    encryptionConfigured: boolean;
    encryptionStatus: "missing" | "invalid" | "valid";
}

interface FaceChallenge {
    challengeId: string;
    direction: "turn_left" | "turn_right";
    prompt: string;
    expiresAt: string;
    ttlSeconds: number;
}

interface FaceVerificationResponse {
    detail: string;
    status: string;
    attendanceRecordId: number;
    recordedAt: string;
}

interface FacePreviewResponse {
    status: string;
    ready: boolean;
    faceCount: number;
    message: string;
    boundingBox: { x: number; y: number; width: number; height: number } | null;
    poseRatio: number | null;
}


function getCameraErrorMessage(error: unknown): string {
    const name = error instanceof DOMException ? error.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        return "Allow camera access in your browser settings, then try again.";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        return "No camera was found on this device.";
    }
    if (name === "NotReadableError" || name === "TrackStartError") {
        return "Your camera is being used by another app. Close it and try again.";
    }
    if (name === "OverconstrainedError") {
        return "Your camera could not start with these settings. Try again.";
    }
    return "We could not open your camera. Check your browser settings and try again.";
}

function useCamera(enabled: boolean) {
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const [cameraError, setCameraError] = useState("");
    const [cameraReady, setCameraReady] = useState(false);

    useEffect(() => {
        if (!enabled) return;
        let disposed = false;

        async function startCamera() {
            setCameraError("");
            setCameraReady(false);
            try {
                if (!navigator.mediaDevices?.getUserMedia) {
                    throw new DOMException("Camera access is unavailable.", "NotSupportedError");
                }
                const isMobileViewport = window.matchMedia("(max-width: 760px)").matches;
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: {
                        facingMode: { ideal: "user" },
                        width: { ideal: isMobileViewport ? 720 : 1280 },
                        height: { ideal: isMobileViewport ? 1280 : 720 },
                        aspectRatio: { ideal: isMobileViewport ? 0.8 : 16 / 9 },
                    },
                });
                if (disposed) {
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                streamRef.current = stream;
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    await videoRef.current.play();
                    setCameraReady(true);
                }
            } catch (error) {
                if (!disposed) {
                    setCameraError(getCameraErrorMessage(error));
                }
            }
        }

        void startCamera();
        return () => {
            disposed = true;
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
            setCameraReady(false);
        };
    }, [enabled]);

    async function captureFrame(maxWidth = 640, quality = 0.78): Promise<Blob> {
        const video = videoRef.current;
        if (!video || !video.videoWidth || !video.videoHeight) {
            throw new Error("The camera is not ready. Wait for the video preview and try again.");
        }

        const displayRect = video.getBoundingClientRect();
        const targetAspect = displayRect.width > 0 && displayRect.height > 0
            ? displayRect.width / displayRect.height
            : video.videoWidth / video.videoHeight;
        const sourceAspect = video.videoWidth / video.videoHeight;
        let sourceX = 0;
        let sourceY = 0;
        let sourceWidth = video.videoWidth;
        let sourceHeight = video.videoHeight;

        // Crop the source to the exact visible camera viewport. This keeps the
        // image sent to Django consistent with what the student sees on mobile.
        if (sourceAspect > targetAspect) {
            sourceWidth = video.videoHeight * targetAspect;
            sourceX = (video.videoWidth - sourceWidth) / 2;
        } else if (sourceAspect < targetAspect) {
            sourceHeight = video.videoWidth / targetAspect;
            sourceY = (video.videoHeight - sourceHeight) / 2;
        }

        const scale = Math.min(1, maxWidth / sourceWidth);
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(320, Math.round(sourceWidth * scale));
        canvas.height = Math.max(240, Math.round(sourceHeight * (canvas.width / sourceWidth)));
        const context = canvas.getContext("2d");
        if (!context) throw new Error("The camera frame could not be prepared.");
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
        context.drawImage(
            video,
            sourceX,
            sourceY,
            sourceWidth,
            sourceHeight,
            0,
            0,
            canvas.width,
            canvas.height,
        );
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error("The camera frame could not be captured."));
            }, "image/jpeg", quality);
        });
    }

    return {
        videoRef,
        cameraError,
        cameraReady,
        captureFrame: () => captureFrame(1280, 0.88),
        capturePreviewFrame: () => captureFrame(640, 0.72),
    };
}

export function BiometricSettingsPage() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [acknowledged, setAcknowledged] = useState(false);
    const [cameraEnabled, setCameraEnabled] = useState(false);
    const [frames, setFrames] = useState<Blob[]>([]);
    const [pageError, setPageError] = useState("");
    const [livePreview, setLivePreview] = useState<FacePreviewResponse>({
        status: "waiting",
        ready: false,
        faceCount: 0,
        message: "Getting the camera ready…",
        boundingBox: null,
        poseRatio: null,
    });
    const camera = useCamera(cameraEnabled);
    const previewInFlightRef = useRef(false);
    const stableFramesRef = useRef(0);
    const baselinePoseRef = useRef<number | null>(null);
    const framesRef = useRef<Blob[]>([]);

    const statusQuery = useQuery({
        queryKey: ["biometrics", "status"],
        queryFn: () => apiRequest<BiometricStatus>("/api/v1/biometrics/status/"),
    });

    const consentMutation = useMutation({
        mutationFn: (action: "granted" | "withdrawn") => apiRequest<BiometricStatus & { detail: string }>("/api/v1/biometrics/consent/", {
            method: "POST",
            body: JSON.stringify({
                action,
                policyVersion: statusQuery.data?.currentPolicyVersion,
                acknowledged: action === "granted" ? acknowledged : true,
            }),
        }),
        onSuccess: async () => {
            setAcknowledged(false);
            setCameraEnabled(false);
            setFrames([]);
            framesRef.current = [];
            stableFramesRef.current = 0;
            baselinePoseRef.current = null;
            await queryClient.invalidateQueries({ queryKey: ["biometrics"] });
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "The consent preference could not be updated."),
    });

    const enrollmentMutation = useMutation({
        mutationFn: (capturedFrames: Blob[]) => {
            const formData = new FormData();
            capturedFrames.forEach((frame) => formData.append("frames", frame, "enrolment-frame.jpg"));
            return apiRequest<{ detail: string }>("/api/v1/biometrics/enrolment/", {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: async () => {
            setCameraEnabled(false);
            setFrames([]);
            framesRef.current = [];
            stableFramesRef.current = 0;
            baselinePoseRef.current = null;
            setPageError("");
            await queryClient.invalidateQueries({ queryKey: ["biometrics"] });
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "Face setup could not be completed."),
    });

    const deleteMutation = useMutation({
        mutationFn: () => apiRequest<{ detail: string }>("/api/v1/biometrics/enrolment/", { method: "DELETE" }),
        onSuccess: async () => {
            setPageError("");
            await queryClient.invalidateQueries({ queryKey: ["biometrics"] });
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "Your face record could not be removed. Please try again."),
    });

    const status = statusQuery.data;
    const consentGranted = status?.consentStatus === "granted";

    useEffect(() => {
        if (!cameraEnabled || !camera.cameraReady || frames.length >= 3 || enrollmentMutation.isPending) {
            return;
        }

        let disposed = false;

        async function inspectLiveFrame() {
            if (previewInFlightRef.current || disposed) return;
            previewInFlightRef.current = true;
            try {
                const frame = await camera.capturePreviewFrame();
                const formData = new FormData();
                formData.append("frame", frame, "live-face-preview.jpg");
                const result = await apiRequest<FacePreviewResponse>("/api/v1/biometrics/face-preview/", {
                    method: "POST",
                    body: formData,
                });
                if (disposed) return;

                const stage = framesRef.current.length;
                setLivePreview(result);
                if (!result.ready || result.poseRatio === null) {
                    stableFramesRef.current = 0;
                    return;
                }

                const baseline = baselinePoseRef.current;
                const poseReady = stage === 0
                    ? Math.abs(result.poseRatio - 0.5) <= 0.10
                    : stage === 1
                        ? baseline !== null && result.poseRatio <= baseline - 0.08
                        : baseline !== null && result.poseRatio >= baseline + 0.08;

                if (!poseReady) {
                    stableFramesRef.current = 0;
                    setLivePreview({
                        ...result,
                        message: stage === 0
                            ? "Look straight at the camera."
                            : stage === 1
                                ? "Turn slightly left."
                                : "Turn slightly right.",
                    });
                    return;
                }

                stableFramesRef.current += 1;
                setLivePreview({ ...result, message: "Good. Hold still…" });
                if (stableFramesRef.current < 2) return;

                const nextFrames = [...framesRef.current, frame].slice(0, 3);
                framesRef.current = nextFrames;
                setFrames(nextFrames);
                if (stage === 0) baselinePoseRef.current = result.poseRatio;
                stableFramesRef.current = 0;

                if (nextFrames.length === 3) {
                    setCameraEnabled(false);
                    setLivePreview({
                        status: "captured",
                        ready: true,
                        faceCount: 1,
                        message: "Your face has been captured. Finishing setup…",
                        boundingBox: null,
                        poseRatio: null,
                    });
                    enrollmentMutation.mutate(nextFrames);
                } else {
                    setLivePreview({
                        ...result,
                        status: "captured",
                        ready: true,
                        message: `${nextFrames.length} of 3 frames captured. Follow the next prompt.`,
                    });
                }
            } catch (error) {
                if (!disposed) {
                    stableFramesRef.current = 0;
                    setLivePreview({
                        status: "unavailable",
                        ready: false,
                        faceCount: 0,
                        message: error instanceof Error ? error.message : "Live face detection is temporarily unavailable.",
                        boundingBox: null,
                        poseRatio: null,
                    });
                }
            } finally {
                previewInFlightRef.current = false;
            }
        }

        const timer = window.setInterval(() => void inspectLiveFrame(), 900);
        void inspectLiveFrame();
        return () => {
            disposed = true;
            window.clearInterval(timer);
        };
    }, [cameraEnabled, camera.cameraReady, frames.length, enrollmentMutation.isPending]);

    if (user?.role !== "student") return <Navigate to="/app" replace />;

    function startEnrollmentCamera() {
        enrollmentMutation.reset();
        framesRef.current = [];
        stableFramesRef.current = 0;
        baselinePoseRef.current = null;
        setFrames([]);
        setPageError("");
        setLivePreview({
            status: "waiting",
            ready: false,
            faceCount: 0,
            message: "Getting the camera ready…",
            boundingBox: null,
            poseRatio: null,
        });
        setCameraEnabled(true);
    }

    function retryEnrollmentCamera() {
        setCameraEnabled(false);
        window.setTimeout(() => setCameraEnabled(true), 120);
    }

    function resetEnrollmentCapture() {
        enrollmentMutation.reset();
        setCameraEnabled(false);
        framesRef.current = [];
        stableFramesRef.current = 0;
        baselinePoseRef.current = null;
        setFrames([]);
        setLivePreview({
            status: "waiting",
            ready: false,
            faceCount: 0,
            message: "Ready when you are.",
            boundingBox: null,
            poseRatio: null,
        });
    }

    function submitEnrollment() {
        if (frames.length !== 3) return;
        enrollmentMutation.mutate(frames);
    }

    return (
        <div className="dashboard-page biometric-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div>
                    <h1>Face verification</h1>
                    <p>Set up and manage face verification for attendance.</p>
                </div>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance</Link>

            {pageError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{pageError}</div>}
            {statusQuery.isLoading && <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading…</div>}
            {statusQuery.isError && <div className="workspace-alert workspace-alert-error">{statusQuery.error instanceof Error ? statusQuery.error.message : "We could not load your face settings."}</div>}

            {status && (
                <>
                    <section className="biometric-status-card">
                        <div className="biometric-status-icon"><ShieldCheck size={24} /></div>
                        <div className="biometric-status-copy">
                            <span className="eyebrow">YOUR STATUS</span>
                            <h2>{status.consentStatus === "consent_update_required" ? "Review the updated notice" : status.isEnrolled ? "Face verification is ready" : consentGranted ? "Ready to set up" : "Not set up"}</h2>
                            <p>{status.isEnrolled ? `Set up on ${status.enrolledAt ? new Date(status.enrolledAt).toLocaleDateString() : "your account"}.` : "Set up face verification to check in automatically."}</p>
                        </div>
                        <span className={`workspace-status ${status.isEnrolled && status.consentStatus !== "consent_update_required" ? "is-positive" : "is-neutral"}`}>{status.consentStatus === "consent_update_required" ? "Review needed" : status.isEnrolled ? "Ready" : "Not set up"}</span>
                    </section>

                    {!consentGranted ? (
                        <section className="biometric-panel">
                            <span className="eyebrow">BEFORE YOU CONTINUE</span>
                            <h2>About face verification</h2>
                            <p>RollNexa uses your face to confirm your identity at check-in. Camera images are sent securely for a temporary check. We store an encrypted face record, not your photographs.</p>
                            <ul className="biometric-policy-list">
                                <li>Setting up face verification is optional.</li>
                                <li>You can withdraw consent and remove your face record at any time.</li>
                                <li>If you do not use face verification, your lecturer can record an approved alternative.</li>
                                <li>Camera images are processed temporarily and are not saved as photographs.</li>
                            </ul>
                            <label className="biometric-consent-check">
                                <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
                                <span>I have read this notice and agree to use face verification for attendance.</span>
                            </label>
                            <div className="biometric-action-row">
                                <button className="button button-primary" type="button" disabled={!acknowledged || consentMutation.isPending} onClick={() => consentMutation.mutate("granted")}>
                                    {consentMutation.isPending ? <LoaderCircle size={16} className="workspace-spin" /> : <ShieldCheck size={16} />} Continue
                                </button>
                                {status.consentStatus === "consent_update_required" && (
                                    <button className="button button-outline" type="button" disabled={consentMutation.isPending} onClick={() => { if (window.confirm("Withdraw your previous face verification consent and delete any stored face record?")) consentMutation.mutate("withdrawn"); }}>Withdraw and delete face record</button>
                                )}
                            </div>
                        </section>
                    ) : (
                        <section className="biometric-panel">
                            <div className="biometric-panel-heading">
                                <div><span className="eyebrow">FACE VERIFICATION</span><h2>{status.isEnrolled ? "Face verification is ready" : "Set up face verification"}</h2></div>
                                <span className="workspace-status is-positive">Consent given</span>
                            </div>
                            <p>{status.isEnrolled ? "Your face is set up for attendance check-in." : "Follow the on-screen guidance. RollNexa will capture each view automatically."}</p>
                            {!status.modelsAvailable && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />Face verification is temporarily unavailable. Please try again later.</div>}
                            {status.encryptionStatus === "missing" && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />Face verification is temporarily unavailable. Please contact your institution.</div>}
                            {status.encryptionStatus === "invalid" && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />Face verification is temporarily unavailable. Please contact your institution.</div>}
                            {!status.isEnrolled && !cameraEnabled && frames.length < 3 && (
                                <button className="button button-primary" type="button" disabled={!status.modelsAvailable || status.encryptionStatus !== "valid"} onClick={startEnrollmentCamera}><Camera size={16} /> Set up face verification</button>
                            )}
                            {cameraEnabled && (
                                <div className="biometric-capture-layout biometric-live-capture">
                                    <div className="biometric-camera-frame">
                                        <video ref={camera.videoRef} autoPlay playsInline muted />
                                        <div className="biometric-face-guide" aria-hidden="true" />
                                        {livePreview.boundingBox && (
                                            <div
                                                className="biometric-face-box"
                                                style={{
                                                    left: `${livePreview.boundingBox.x * 100}%`,
                                                    top: `${livePreview.boundingBox.y * 100}%`,
                                                    width: `${livePreview.boundingBox.width * 100}%`,
                                                    height: `${livePreview.boundingBox.height * 100}%`,
                                                }}
                                            />
                                        )}
                                    </div>
                                    <div className="biometric-capture-controls">
                                        <span className="biometric-stage-label">VIEW {Math.min(frames.length + 1, 3)} OF 3</span>
                                        <strong>{frames.length === 0 ? "Look at the camera" : frames.length === 1 ? "Turn slightly left" : "Turn slightly right"}</strong>
                                        <p>Use even lighting and keep your face in the frame. Each view is captured automatically.</p>
                                        <div className={`biometric-live-status ${livePreview.ready ? "is-ready" : ""}`} role="status" aria-live="polite">
                                            <span className="biometric-live-indicator" />
                                            <span>{camera.cameraReady ? livePreview.message : camera.cameraError || "Waiting for camera permission…"}</span>
                                        </div>
                                        {camera.cameraError && (
                                            <div className="biometric-camera-error">
                                                <div className="workspace-alert workspace-alert-error">{camera.cameraError}</div>
                                                <button className="button button-outline" type="button" onClick={retryEnrollmentCamera}>Try camera again</button>
                                            </div>
                                        )}
                                        <div className="biometric-frame-progress" aria-label={`${frames.length} of 3 frames captured`}>
                                            {[0, 1, 2].map((index) => <span key={index} className={index < frames.length ? "is-complete" : ""} />)}
                                        </div>
                                        <div className="biometric-action-row">
                                            <button className="button button-outline" type="button" onClick={resetEnrollmentCapture}>Cancel capture</button>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {frames.length === 3 && !cameraEnabled && (
                                <div className="biometric-enrollment-ready" role="status" aria-live="polite">
                                    {enrollmentMutation.isPending ? <LoaderCircle size={20} className="workspace-spin" /> : <CheckCircle2 size={20} />}
                                    <div>
                                        <strong>{enrollmentMutation.isPending ? "Finishing setup…" : "Setup could not be completed"}</strong>
                                        <p>{enrollmentMutation.isPending ? "Saving your face record securely." : "Check your connection and try again."}</p>
                                    </div>
                                    {enrollmentMutation.isError && (
                                        <div className="biometric-action-row">
                                            <button className="button button-primary" type="button" onClick={submitEnrollment}>Try again</button>
                                            <button className="button button-outline" type="button" onClick={resetEnrollmentCapture}>Start again</button>
                                        </div>
                                    )}
                                </div>
                            )}
                            {status.isEnrolled && (
                                <div className="biometric-action-row">
                                    <button className="button button-outline" type="button" disabled={deleteMutation.isPending} onClick={() => { if (window.confirm("Remove your saved face record? You can set it up again while consent remains active.")) deleteMutation.mutate(); }}><Trash2 size={15} /> Remove face record</button>
                                </div>
                            )}
                            <div className="biometric-withdraw-row">
                                <div><strong>Withdraw consent</strong><p>Your face record will be deleted and any pending check-in will be cancelled.</p></div>
                                <button className="button button-outline" type="button" disabled={consentMutation.isPending} onClick={() => { if (window.confirm("Withdraw consent and delete your saved face record? You can still check in using an approved alternative.")) consentMutation.mutate("withdrawn"); }}>Withdraw consent</button>
                            </div>
                        </section>
                    )}
                    <div className="biometric-alternative-note"><ShieldCheck size={18} /><p><strong>Need another way to check in?</strong> Your lecturer can record an approved alternative if you do not use face verification or cannot complete it.</p></div>
                </>
            )}
        </div>
    );
}

export function AttendanceFaceCheckPage() {
    const { user } = useAuth();
    const { verificationId = "" } = useParams();
    const queryClient = useQueryClient();
    const [cameraEnabled, setCameraEnabled] = useState(false);
    const [pageError, setPageError] = useState("");
    const [livePreview, setLivePreview] = useState<FacePreviewResponse>({
        status: "waiting",
        ready: false,
        faceCount: 0,
        message: "Getting the camera ready…",
        boundingBox: null,
        poseRatio: null,
    });
    const [verificationStage, setVerificationStage] = useState<"aligning" | "turning" | "checking" | "failed">("aligning");
    const camera = useCamera(cameraEnabled);
    const baselineFrameRef = useRef<Blob | null>(null);
    const baselinePoseRef = useRef<number | null>(null);
    const stableFramesRef = useRef(0);
    const previewInFlightRef = useRef(false);
    const verificationSubmittedRef = useRef(false);
    const challengeRequestedRef = useRef(false);

    const biometricQuery = useQuery({
        queryKey: ["biometrics", "status"],
        queryFn: () => apiRequest<BiometricStatus>("/api/v1/biometrics/status/"),
    });
    const verificationQuery = useQuery({
        queryKey: ["attendance-verification", verificationId],
        queryFn: () => apiRequest<{ status: string; expiresAt: string }>(`/api/v1/attendance/verifications/${verificationId}/`),
        enabled: Boolean(verificationId),
    });
    const challengeMutation = useMutation({
        mutationFn: () => apiRequest<FaceChallenge>(`/api/v1/biometrics/verifications/${verificationId}/challenge/`, {
            method: "POST",
            body: JSON.stringify({}),
        }),
        onSuccess: () => {
            baselineFrameRef.current = null;
            baselinePoseRef.current = null;
            stableFramesRef.current = 0;
            verificationSubmittedRef.current = false;
            setPageError("");
            setVerificationStage("aligning");
            setCameraEnabled(true);
        },
        onError: (error) => {
            setVerificationStage("failed");
            setPageError(error instanceof Error ? error.message : "We could not start face verification.");
        },
    });
    const faceMutation = useMutation({
        mutationFn: async (frames: { baselineFrame: Blob; challengeFrame: Blob }) => {
            const challenge = challengeMutation.data;
            if (!challenge) throw new Error("Please restart the face check.");
            const formData = new FormData();
            formData.append("challengeId", challenge.challengeId);
            formData.append("baselineFrame", frames.baselineFrame, "reference-frame.jpg");
            formData.append("challengeFrame", frames.challengeFrame, "challenge-frame.jpg");
            return apiRequest<FaceVerificationResponse>(`/api/v1/biometrics/verifications/${verificationId}/verify/`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: async () => {
            setCameraEnabled(false);
            setPageError("");
            setVerificationStage("checking");
            await queryClient.invalidateQueries({ queryKey: ["workspace"] });
            await queryClient.invalidateQueries({ queryKey: ["attendance-verification", verificationId] });
            await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        },
        onError: async (error) => {
            setCameraEnabled(false);
            setVerificationStage("failed");
            setPageError(error instanceof Error ? error.message : "We could not verify your face. Please try again.");
            await queryClient.invalidateQueries({ queryKey: ["attendance-verification", verificationId] });
        },
    });

    const requestChallenge = useCallback(() => {
        challengeRequestedRef.current = true;
        setPageError("");
        challengeMutation.mutate();
    }, [challengeMutation.mutate]);

    useEffect(() => {
        if (
            verificationQuery.data?.status === "qr_verified"
            && biometricQuery.data?.isEnrolled
            && biometricQuery.data.consentStatus === "granted"
            && !challengeMutation.data
            && !challengeMutation.isPending
            && !challengeRequestedRef.current
        ) {
            requestChallenge();
        }
    }, [verificationQuery.data?.status, biometricQuery.data?.isEnrolled, biometricQuery.data?.consentStatus, challengeMutation.data, challengeMutation.isPending, requestChallenge]);

    useEffect(() => {
        const challenge = challengeMutation.data;
        if (!cameraEnabled || !camera.cameraReady || !challenge || faceMutation.isPending || faceMutation.isSuccess) {
            return;
        }

        let disposed = false;

        async function inspectLiveFrame() {
            if (previewInFlightRef.current || verificationSubmittedRef.current || disposed) return;
            previewInFlightRef.current = true;

            try {
                if (Date.now() >= new Date(challenge.expiresAt).getTime()) {
                    throw new Error("This check has timed out. Please try again.");
                }

                const previewFrame = await camera.capturePreviewFrame();
                const formData = new FormData();
                formData.append("frame", previewFrame, "live-face-check.jpg");
                const result = await apiRequest<FacePreviewResponse>("/api/v1/biometrics/face-preview/", {
                    method: "POST",
                    body: formData,
                });
                if (disposed) return;

                setLivePreview(result);
                if (!result.ready || result.poseRatio === null) {
                    stableFramesRef.current = 0;
                    setVerificationStage(baselineFrameRef.current ? "turning" : "aligning");
                    return;
                }

                if (!baselineFrameRef.current) {
                    if (Math.abs(result.poseRatio - 0.5) > 0.10) {
                        stableFramesRef.current = 0;
                        setVerificationStage("aligning");
                        setLivePreview({ ...result, message: "Look straight at the camera." });
                        return;
                    }

                    stableFramesRef.current += 1;
                    setVerificationStage("aligning");
                    setLivePreview({ ...result, message: "Good. Hold still…" });
                    if (stableFramesRef.current < 2) return;

                    const baselineFrame = await camera.captureFrame();
                    if (disposed) return;
                    baselineFrameRef.current = baselineFrame;
                    baselinePoseRef.current = result.poseRatio;
                    stableFramesRef.current = 0;
                    setVerificationStage("turning");
                    setLivePreview({
                        ...result,
                        message: challenge.direction === "turn_left" ? "Now turn slightly left." : "Now turn slightly right.",
                    });
                    return;
                }

                const baselinePose = baselinePoseRef.current;
                if (baselinePose === null) return;
                const poseReady = challenge.direction === "turn_left"
                    ? result.poseRatio <= baselinePose - 0.08
                    : result.poseRatio >= baselinePose + 0.08;

                if (!poseReady) {
                    stableFramesRef.current = 0;
                    setVerificationStage("turning");
                    setLivePreview({
                        ...result,
                        message: challenge.direction === "turn_left" ? "Turn a little further left." : "Turn a little further right.",
                    });
                    return;
                }

                stableFramesRef.current += 1;
                setVerificationStage("turning");
                setLivePreview({ ...result, message: "Good. Hold still…" });
                if (stableFramesRef.current < 2) return;

                const baselineFrame = baselineFrameRef.current;
                if (!baselineFrame) throw new Error("Please try the face check again.");
                verificationSubmittedRef.current = true;
                stableFramesRef.current = 0;
                setVerificationStage("checking");
                setLivePreview({ ...result, message: "Checking your attendance…" });
                const challengeFrame = await camera.captureFrame();
                if (disposed) return;
                faceMutation.mutate({ baselineFrame, challengeFrame });
            } catch (error) {
                if (!disposed) {
                    setCameraEnabled(false);
                    setVerificationStage("failed");
                    setPageError(error instanceof Error ? error.message : "We could not complete the face check.");
                }
            } finally {
                previewInFlightRef.current = false;
            }
        }

        const timer = window.setInterval(() => void inspectLiveFrame(), 900);
        void inspectLiveFrame();
        return () => {
            disposed = true;
            window.clearInterval(timer);
        };
    }, [cameraEnabled, camera.cameraReady, challengeMutation.data, faceMutation.isPending, faceMutation.isSuccess]);

    if (user?.role !== "student") return <Navigate to="/app" replace />;
    if (!verificationId) return <Navigate to="/app/attendance" replace />;

    const biometricStatus = biometricQuery.data;
    const challenge = challengeMutation.data;
    const isComplete = faceMutation.isSuccess || verificationQuery.data?.status === "completed";
    const attemptEnded = verificationQuery.data && ["failed", "expired"].includes(verificationQuery.data.status);

    function retryFaceCheck() {
        setCameraEnabled(false);
        baselineFrameRef.current = null;
        baselinePoseRef.current = null;
        stableFramesRef.current = 0;
        previewInFlightRef.current = false;
        verificationSubmittedRef.current = false;
        challengeRequestedRef.current = false;
        challengeMutation.reset();
        faceMutation.reset();
        setPageError("");
        setVerificationStage("aligning");
        requestChallenge();
    }

    function retryCamera() {
        setPageError("");
        setCameraEnabled(false);
        window.setTimeout(() => setCameraEnabled(true), 120);
    }

    return (
        <div className="dashboard-page biometric-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div>
                    <h1>Confirm attendance</h1>
                    <p>Look at the camera and follow the short instruction. We will finish automatically.</p>
                </div>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance</Link>
            {pageError && <div className="workspace-alert workspace-alert-error" role="alert"><AlertCircle size={17} />{pageError}</div>}

            {isComplete ? (
                <section className="attendance-verification-result">
                    <span className="attendance-result-icon"><CheckCircle2 size={30} /></span>
                    <h2>You're checked in</h2>
                    <p>Your attendance has been recorded.</p>
                    <div className="attendance-result-actions"><Link to="/app/history" className="button button-primary">View attendance</Link></div>
                </section>
            ) : biometricQuery.isLoading || verificationQuery.isLoading ? (
                <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Preparing check-in…</div>
            ) : biometricQuery.isError || verificationQuery.isError ? (
                <section className="biometric-panel">
                    <h2>We couldn't prepare check-in</h2>
                    <p>Refresh the page and try again.</p>
                    <button className="button button-primary" type="button" onClick={() => { void biometricQuery.refetch(); void verificationQuery.refetch(); }}>Try again</button>
                </section>
            ) : attemptEnded ? (
                <section className="biometric-panel">
                    <h2>This check-in has ended</h2>
                    <p>Scan the current class code to try again.</p>
                    <Link to="/app/attendance/check-in" className="button button-primary">Scan QR Code</Link>
                </section>
            ) : biometricStatus && (!biometricStatus.isEnrolled || biometricStatus.consentStatus !== "granted") ? (
                <section className="biometric-panel">
                    <h2>Set up face verification first</h2>
                    <p>Complete the face setup before checking in. You can also ask your lecturer for an approved alternative.</p>
                    <Link to="/app/biometrics" className="button button-primary">Set up face verification</Link>
                </section>
            ) : verificationQuery.data?.status !== "qr_verified" ? (
                <section className="biometric-panel">
                    <h2>This check-in is not ready</h2>
                    <p>Scan the current class code to start again.</p>
                    <Link to="/app/attendance/check-in" className="button button-primary">Scan class code</Link>
                </section>
            ) : challengeMutation.isPending ? (
                <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Getting the camera ready…</div>
            ) : challengeMutation.isError ? (
                <section className="biometric-panel">
                    <h2>We couldn't start the face check</h2>
                    <p>Check your connection and try again.</p>
                    <button className="button button-primary" type="button" onClick={retryFaceCheck}>Try again</button>
                </section>
            ) : faceMutation.isError || verificationStage === "failed" ? (
                <section className="biometric-panel">
                    <h2>Let's try that again</h2>
                    <p>Keep your face in the frame and follow the prompt.</p>
                    <button className="button button-primary" type="button" onClick={retryFaceCheck}>Try again</button>
                </section>
            ) : camera.cameraError ? (
                <section className="biometric-panel">
                    <h2>Camera access is needed</h2>
                    <p>Allow camera access in your browser, then try again.</p>
                    <button className="button button-primary" type="button" onClick={retryCamera}>Try camera again</button>
                </section>
            ) : (
                <section className="biometric-panel biometric-check-panel">
                    <div className="biometric-check-heading">
                        <span className="biometric-stage-label">{verificationStage === "aligning" ? "POSITION YOUR FACE" : verificationStage === "turning" ? "FOLLOW THE PROMPT" : "CHECKING"}</span>
                        <h2>{verificationStage === "aligning" ? "Look at the camera" : verificationStage === "turning" ? (challenge?.direction === "turn_left" ? "Turn slightly left" : "Turn slightly right") : "Checking your attendance…"}</h2>
                        <p>{verificationStage === "aligning" ? "Keep your face inside the guide." : verificationStage === "turning" ? "Move gently, then hold still." : "This will only take a moment."}</p>
                    </div>
                    <div className="biometric-capture-layout biometric-live-capture biometric-verification-capture">
                        <div className="biometric-camera-frame">
                            <video ref={camera.videoRef} autoPlay playsInline muted />
                            <div className="biometric-face-guide" aria-hidden="true" />
                            {livePreview.boundingBox && (
                                <div
                                    className="biometric-face-box"
                                    style={{
                                        left: `${livePreview.boundingBox.x * 100}%`,
                                        top: `${livePreview.boundingBox.y * 100}%`,
                                        width: `${livePreview.boundingBox.width * 100}%`,
                                        height: `${livePreview.boundingBox.height * 100}%`,
                                    }}
                                />
                            )}
                            {verificationStage === "checking" && <div className="biometric-camera-checking"><LoaderCircle className="workspace-spin" size={25} /><span>Checking…</span></div>}
                        </div>
                        <div className="biometric-capture-controls">
                            <div className="biometric-frame-progress" aria-label={verificationStage === "aligning" ? "Step one of two" : "Step two of two"}>
                                <span className={verificationStage !== "aligning" ? "is-complete" : "is-current"} />
                                <span className={verificationStage === "checking" ? "is-complete" : verificationStage === "turning" ? "is-current" : ""} />
                            </div>
                            <div className={`biometric-live-status ${livePreview.ready ? "is-ready" : ""}`} role="status" aria-live="polite">
                                <span className="biometric-live-indicator" />
                                <span>{camera.cameraReady ? livePreview.message : "Opening camera…"}</span>
                            </div>
                            <p className="biometric-verification-footnote">Use even lighting and keep your face visible.</p>
                        </div>
                    </div>
                </section>
            )}
            <div className="biometric-alternative-note"><ShieldCheck size={18} /><p><strong>Need another way to check in?</strong> Your lecturer can record an approved alternative if you cannot complete face verification.</p></div>
        </div>
    );
}
