import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, Camera, CheckCircle2, LoaderCircle, ScanFace, ShieldCheck, Trash2 } from "lucide-react";
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
                    throw new Error("Camera access requires a supported browser and a secure HTTPS connection.");
                }
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: {
                        facingMode: "user",
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
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
                    setCameraError(error instanceof Error ? error.message : "The camera could not be started.");
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

    async function captureFrame(): Promise<Blob> {
        const video = videoRef.current;
        if (!video || !video.videoWidth || !video.videoHeight) {
            throw new Error("The camera is not ready. Wait for the video preview and try again.");
        }
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("The camera frame could not be prepared.");
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error("The camera frame could not be captured."));
            }, "image/jpeg", 0.88);
        });
    }

    return { videoRef, cameraError, cameraReady, captureFrame };
}

export function BiometricSettingsPage() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [acknowledged, setAcknowledged] = useState(false);
    const [cameraEnabled, setCameraEnabled] = useState(false);
    const [frames, setFrames] = useState<Blob[]>([]);
    const [pageError, setPageError] = useState("");
    const camera = useCamera(cameraEnabled);

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
            setPageError("");
            await queryClient.invalidateQueries({ queryKey: ["biometrics"] });
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "Facial enrolment could not be completed."),
    });

    const deleteMutation = useMutation({
        mutationFn: () => apiRequest<{ detail: string }>("/api/v1/biometrics/enrolment/", { method: "DELETE" }),
        onSuccess: async () => {
            setPageError("");
            await queryClient.invalidateQueries({ queryKey: ["biometrics"] });
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "The facial template could not be deleted."),
    });

    if (user?.role !== "student") return <Navigate to="/app" replace />;
    const status = statusQuery.data;
    const consentGranted = status?.consentStatus === "granted";

    async function captureEnrollmentFrame() {
        setPageError("");
        try {
            const frame = await camera.captureFrame();
            setFrames((current) => [...current, frame].slice(0, 3));
        } catch (error) {
            setPageError(error instanceof Error ? error.message : "The frame could not be captured.");
        }
    }

    function submitEnrollment() {
        if (frames.length !== 3) return;
        enrollmentMutation.mutate(frames);
    }

    return (
        <div className="dashboard-page biometric-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div>
                    <span className="eyebrow">STUDENT WORKSPACE</span>
                    <h1>Biometric settings</h1>
                    <p>Manage your biometric consent and facial enrolment for attendance verification.</p>
                </div>
                <span className="release-chip"><span /> ROLLNEXA 1.0.1</span>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance</Link>

            {pageError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{pageError}</div>}
            {statusQuery.isLoading && <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading biometric settings…</div>}
            {statusQuery.isError && <div className="workspace-alert workspace-alert-error">{statusQuery.error instanceof Error ? statusQuery.error.message : "Biometric settings could not be loaded."}</div>}

            {status && (
                <>
                    <section className="biometric-status-card">
                        <div className="biometric-status-icon"><ShieldCheck size={24} /></div>
                        <div className="biometric-status-copy">
                            <span className="eyebrow">BIOMETRIC STATUS</span>
                            <h2>{status.isEnrolled ? "Facial enrolment complete" : consentGranted ? "Consent granted · enrolment pending" : "Facial enrolment not active"}</h2>
                            <p>{status.isEnrolled ? `Your encrypted facial template was enrolled ${status.enrolledAt ? new Date(status.enrolledAt).toLocaleString() : ""}.` : "A facial template is required for automated attendance verification."}</p>
                        </div>
                        <span className={`workspace-status ${status.isEnrolled ? "is-positive" : "is-neutral"}`}>{status.isEnrolled ? "Enrolled" : "Not enrolled"}</span>
                    </section>

                    {!consentGranted ? (
                        <section className="biometric-panel">
                            <span className="eyebrow">INFORMED CHOICE</span>
                            <h2>Biometric consent</h2>
                            <p>RollNexa will process camera frames on the server to create and compare a facial feature template for attendance identity verification. The system stores an encrypted facial template, not the camera photographs used during enrolment or attendance checks.</p>
                            <ul className="biometric-policy-list">
                                <li>Facial enrolment is optional.</li>
                                <li>You can withdraw consent and request deletion of your stored facial template at any time.</li>
                                <li>Withdrawing consent does not prevent attendance. Ask your lecturer to use the lecturer-approved manual attendance exception process.</li>
                                <li>Camera frames are processed in memory and are not saved as image files by this application.</li>
                            </ul>
                            <label className="biometric-consent-check">
                                <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
                                <span>I have read this notice and voluntarily agree to biometric processing for RollNexa attendance verification.</span>
                            </label>
                            <div className="biometric-action-row">
                                <button className="button button-primary" type="button" disabled={!acknowledged || consentMutation.isPending} onClick={() => consentMutation.mutate("granted")}>
                                    {consentMutation.isPending ? <LoaderCircle size={16} className="workspace-spin" /> : <ShieldCheck size={16} />} Grant biometric consent
                                </button>
                                {status.consentStatus === "consent_update_required" && (
                                    <button className="button button-outline" type="button" disabled={consentMutation.isPending} onClick={() => { if (window.confirm("Withdraw your previous biometric consent and delete any stored facial template?")) consentMutation.mutate("withdrawn"); }}>Withdraw previous consent</button>
                                )}
                            </div>
                        </section>
                    ) : (
                        <section className="biometric-panel">
                            <div className="biometric-panel-heading">
                                <div><span className="eyebrow">ENROLMENT</span><h2>Facial template</h2></div>
                                <span className="workspace-status is-positive">Consent granted</span>
                            </div>
                            <p>Capture three clear images of your face. Keep your face centred, then make small head turns as prompted. The server checks that the captures represent the same person and stores an encrypted feature template.</p>
                            {!status.modelsAvailable && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />Facial recognition model files are not available on this server yet. Enrolment will become available after the deployment installs the model assets.</div>}
                            {!status.encryptionConfigured && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />The biometric encryption key is not configured on this server. The administrator must configure BIOMETRIC_ENCRYPTION_KEY before enrolment.</div>}
                            {!status.isEnrolled && !cameraEnabled && (
                                <button className="button button-primary" type="button" disabled={!status.modelsAvailable || !status.encryptionConfigured} onClick={() => { setFrames([]); setPageError(""); setCameraEnabled(true); }}><Camera size={16} /> Start facial enrolment</button>
                            )}
                            {cameraEnabled && (
                                <div className="biometric-capture-layout">
                                    <div className="biometric-camera-frame"><video ref={camera.videoRef} autoPlay playsInline muted /></div>
                                    <div className="biometric-capture-controls">
                                        <strong>{frames.length === 0 ? "1. Look directly at the camera" : frames.length === 1 ? "2. Turn your head slightly to your left" : frames.length === 2 ? "3. Turn your head slightly to your right" : "All three frames captured"}</strong>
                                        <p>{frames.length} of 3 enrolment frames captured.</p>
                                        {camera.cameraError && <div className="workspace-alert workspace-alert-error">{camera.cameraError}</div>}
                                        <div className="biometric-action-row">
                                            <button className="button button-outline" type="button" disabled={!camera.cameraReady || frames.length >= 3} onClick={() => void captureEnrollmentFrame()}><Camera size={15} /> Capture frame</button>
                                            <button className="button button-primary" type="button" disabled={frames.length !== 3 || enrollmentMutation.isPending} onClick={submitEnrollment}>{enrollmentMutation.isPending ? <LoaderCircle size={15} className="workspace-spin" /> : <ScanFace size={15} />} Submit enrolment</button>
                                            <button className="button button-outline" type="button" onClick={() => { setCameraEnabled(false); setFrames([]); }}>Cancel</button>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {status.isEnrolled && (
                                <div className="biometric-action-row">
                                    <button className="button button-outline" type="button" disabled={deleteMutation.isPending} onClick={() => { if (window.confirm("Delete your stored facial template? You can enrol again while consent remains active.")) deleteMutation.mutate(); }}><Trash2 size={15} /> Delete facial template</button>
                                </div>
                            )}
                            <div className="biometric-withdraw-row">
                                <div><strong>Withdraw consent</strong><p>Withdrawal immediately deletes the stored facial template and expires pending QR verification attempts.</p></div>
                                <button className="button button-outline" type="button" disabled={consentMutation.isPending} onClick={() => { if (window.confirm("Withdraw biometric consent and delete your stored facial template? You can still attend through a lecturer-approved manual exception.")) consentMutation.mutate("withdrawn"); }}>Withdraw consent</button>
                            </div>
                        </section>
                    )}
                    <div className="biometric-alternative-note"><ShieldCheck size={18} /><p><strong>Alternative attendance remains available.</strong> If you do not enrol, withdraw consent or cannot complete facial verification, contact your lecturer for a recorded manual attendance exception. It is kept separate from automated dual verification.</p></div>
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
    const [baselineFrame, setBaselineFrame] = useState<Blob | null>(null);
    const [pageError, setPageError] = useState("");
    const camera = useCamera(cameraEnabled);

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
            setBaselineFrame(null);
            setPageError("");
            setCameraEnabled(true);
        },
        onError: (error) => setPageError(error instanceof Error ? error.message : "A facial challenge could not be created."),
    });
    const faceMutation = useMutation({
        mutationFn: async (challengeFrame: Blob) => {
            if (!challengeMutation.data || !baselineFrame) throw new Error("Capture both required camera frames.");
            const formData = new FormData();
            formData.append("challengeId", challengeMutation.data.challengeId);
            formData.append("baselineFrame", baselineFrame, "baseline-frame.jpg");
            formData.append("challengeFrame", challengeFrame, "challenge-frame.jpg");
            return apiRequest<FaceVerificationResponse>(`/api/v1/biometrics/verifications/${verificationId}/verify/`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: async () => {
            setCameraEnabled(false);
            setPageError("");
            await queryClient.invalidateQueries({ queryKey: ["workspace"] });
            await queryClient.invalidateQueries({ queryKey: ["attendance-verification", verificationId] });
            await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        },
        onError: async (error) => {
            setPageError(error instanceof Error ? error.message : "Facial verification could not be completed.");
            await queryClient.invalidateQueries({ queryKey: ["attendance-verification", verificationId] });
        },
    });

    if (user?.role !== "student") return <Navigate to="/app" replace />;
    const biometricStatus = biometricQuery.data;
    const challenge = challengeMutation.data;
    const isComplete = faceMutation.isSuccess || verificationQuery.data?.status === "completed";

    async function captureBaseline() {
        setPageError("");
        try {
            setBaselineFrame(await camera.captureFrame());
        } catch (error) {
            setPageError(error instanceof Error ? error.message : "The camera frame could not be captured.");
        }
    }

    async function captureChallenge() {
        setPageError("");
        try {
            const frame = await camera.captureFrame();
            faceMutation.mutate(frame);
        } catch (error) {
            setPageError(error instanceof Error ? error.message : "The camera frame could not be captured.");
        }
    }

    function retryChallenge() {
        setCameraEnabled(false);
        setBaselineFrame(null);
        faceMutation.reset();
        challengeMutation.reset();
        setPageError("");
    }

    if (!verificationId) return <Navigate to="/app/attendance" replace />;

    return (
        <div className="dashboard-page biometric-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div><span className="eyebrow">STUDENT WORKSPACE</span><h1>Facial attendance verification</h1><p>Complete the second verification stage for your QR-verified attendance session.</p></div>
                <span className="release-chip"><span /> ROLLNEXA 1.0.1</span>
            </div>
            <Link to="/app/attendance/check-in" className="attendance-back-link"><ArrowLeft size={16} /> Back to QR scanning</Link>
            {pageError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{pageError}</div>}

            {isComplete ? (
                <section className="attendance-verification-result">
                    <span className="attendance-result-icon"><CheckCircle2 size={30} /></span>
                    <span className="eyebrow">DUAL VERIFICATION COMPLETE</span>
                    <h2>Attendance recorded successfully</h2>
                    <p>Both the QR Code and server-side facial verification succeeded. Your attendance record is now available in your history.</p>
                    <div className="attendance-result-actions"><Link to="/app/history" className="button button-primary">View attendance history</Link><Link to="/app/attendance" className="button button-outline">Return to attendance</Link></div>
                </section>
            ) : biometricQuery.isLoading || verificationQuery.isLoading ? (
                <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Preparing verification…</div>
            ) : verificationQuery.data && ["failed", "expired"].includes(verificationQuery.data.status) ? (
                <section className="biometric-panel"><h2>Verification attempt is no longer active</h2><p>This attempt has expired or reached its maximum number of failed facial checks. Scan the lecturer's current QR Code to start a new attendance attempt.</p><Link to="/app/attendance/check-in" className="button button-primary">Scan a new QR Code</Link></section>
            ) : biometricStatus && (!biometricStatus.isEnrolled || biometricStatus.consentStatus !== "granted") ? (
                <section className="biometric-panel"><h2>Facial enrolment is required</h2><p>Complete biometric consent and enrolment before using automated facial verification. You may also ask your lecturer to record an approved manual attendance exception.</p><Link to="/app/biometrics" className="button button-primary">Open biometric settings</Link></section>
            ) : !cameraEnabled && !challenge ? (
                <section className="biometric-panel"><span className="eyebrow">SECOND VERIFICATION STAGE</span><h2>Confirm your identity</h2><p>RollNexa will request two live camera frames. The server checks your enrolled facial template and asks you to perform a short head movement.</p><button className="button button-primary" type="button" disabled={challengeMutation.isPending || verificationQuery.data?.status !== "qr_verified"} onClick={() => challengeMutation.mutate()}>{challengeMutation.isPending ? <LoaderCircle size={16} className="workspace-spin" /> : <ScanFace size={16} />} Start facial verification</button></section>
            ) : (
                <section className="biometric-panel">
                    <span className="eyebrow">LIVE CAMERA CHALLENGE</span>
                    <h2>{baselineFrame ? challenge?.prompt : "Look directly at the camera"}</h2>
                    <p>{baselineFrame ? "Turn your head toward the requested side, keep your face visible and capture the second frame." : "Keep your face centred, look toward the camera and capture a neutral reference frame."}</p>
                    <div className="biometric-capture-layout">
                        <div className="biometric-camera-frame"><video ref={camera.videoRef} autoPlay playsInline muted /></div>
                        <div className="biometric-capture-controls">
                            <strong>{baselineFrame ? "Second frame" : "Reference frame"}</strong>
                            <p>{challenge ? `Challenge expires at ${new Date(challenge.expiresAt).toLocaleTimeString()}.` : "Waiting for camera permission."}</p>
                            {camera.cameraError && <div className="workspace-alert workspace-alert-error">{camera.cameraError}</div>}
                            <div className="biometric-action-row">
                                {!baselineFrame ? <button className="button button-primary" type="button" disabled={!camera.cameraReady} onClick={() => void captureBaseline()}><Camera size={15} /> Capture reference</button> : <button className="button button-primary" type="button" disabled={!camera.cameraReady || faceMutation.isPending} onClick={() => void captureChallenge()}>{faceMutation.isPending ? <LoaderCircle size={15} className="workspace-spin" /> : <ScanFace size={15} />} Capture challenge</button>}
                                <button className="button button-outline" type="button" onClick={retryChallenge}>Restart challenge</button>
                            </div>
                        </div>
                    </div>
                    {faceMutation.isPending && <div className="workspace-alert workspace-alert-info"><LoaderCircle className="workspace-spin" size={16} /> Verifying your face securely on the server…</div>}
                </section>
            )}
            <div className="biometric-alternative-note"><ShieldCheck size={18} /><p><strong>Privacy and alternative.</strong> Captured frames are processed in memory and are not stored as image files. If the camera is unavailable or verification cannot be completed, contact your lecturer for a manual attendance exception.</p></div>
        </div>
    );
}
