import { useCallback, useEffect, useRef, useState } from "react";
import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, Camera, CheckCircle2, Clock3, LoaderCircle, QrCode, RefreshCw, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";

interface AttendanceSessionData {
    id: number;
    title: string;
    course_code: string;
    course_title: string;
    programme_name: string;
    academic_session: string;
    semester_name: string;
    starts_at: string;
    ends_at: string;
    status: string;
    is_open: boolean;
}

interface QrTokenResponse {
    token: string;
    issuedAt: string;
    expiresAt: string;
    ttlSeconds: number;
    session: {
        id: number;
        title: string;
        courseCode: string;
        courseTitle: string;
    };
}

interface VerificationResponse {
    verificationId: string;
    status: string;
    qrVerifiedAt: string;
    faceVerifiedAt: string | null;
    expiresAt: string;
    alreadyVerified: boolean;
    session: {
        id: number;
        title: string;
        courseCode: string;
        courseTitle: string;
        academicSession: string;
        semester: string;
    };
}

const QR_ROTATION_INTERVAL = 30_000;

export function AttendanceQRPage() {
    const { user } = useAuth();
    const { sessionId = "" } = useParams();
    const parsedSessionId = Number(sessionId);

    const sessionQuery = useQuery({
        queryKey: ["workspace", "attendance-sessions", parsedSessionId],
        queryFn: () => apiRequest<{ item: AttendanceSessionData }>(`/api/v1/workspace/attendance-sessions/${parsedSessionId}/`),
        enabled: user?.role === "lecturer" && Number.isInteger(parsedSessionId) && parsedSessionId > 0,
        retry: false,
        refetchInterval: 15_000,
        refetchOnWindowFocus: true,
    });

    const qrQuery = useQuery({
        queryKey: ["attendance-qr", parsedSessionId],
        queryFn: () => apiRequest<QrTokenResponse>(`/api/v1/attendance/sessions/${parsedSessionId}/qr/`),
        enabled: user?.role === "lecturer" && sessionQuery.data?.item.status === "active" && Boolean(sessionQuery.data?.item.is_open),
        refetchInterval: QR_ROTATION_INTERVAL,
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: true,
        gcTime: 0,
        retry: false,
    });

    const [now, setNow] = useState(Date.now());
    useEffect(() => {
        const timer = window.setInterval(() => setNow(Date.now()), 1000);
        return () => window.clearInterval(timer);
    }, []);

    if (user?.role !== "lecturer" || !Number.isInteger(parsedSessionId) || parsedSessionId <= 0) {
        return <Navigate to="/app/attendance" replace />;
    }

    const session = sessionQuery.data?.item;
    const qrData = qrQuery.data;
    const expiresAt = qrData ? new Date(qrData.expiresAt).getTime() : 0;
    const secondsRemaining = qrData ? Math.max(0, Math.ceil((expiresAt - now) / 1000)) : 0;
    const qrValue = qrData
        ? `${window.location.origin}/app/attendance/check-in?token=${encodeURIComponent(qrData.token)}`
        : "";

    return (
        <div className="dashboard-page attendance-qr-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div>
                    <span className="eyebrow">LECTURER WORKSPACE</span>
                    <h1>Live attendance QR Code</h1>
                    <p>Display this rotating code for students registered in the selected course offering.</p>
                </div>
                <span className="release-chip"><span /> ROLLNEXA 1.0.0</span>
            </div>

            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance sessions</Link>

            {sessionQuery.isLoading && <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading attendance session…</div>}
            {sessionQuery.isError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />This attendance session could not be loaded. It may not belong to an active teaching assignment.</div>}

            {session && (
                <div className="attendance-qr-layout">
                    <section className="attendance-qr-card">
                        <div className="attendance-qr-card-heading">
                            <span className="attendance-qr-icon"><QrCode size={21} /></span>
                            <div>
                                <span className="eyebrow">{session.course_code}</span>
                                <h2>{session.title || "Attendance session"}</h2>
                                <p>{session.course_title}</p>
                            </div>
                        </div>

                        {session.status !== "active" || !session.is_open ? (
                            <div className="attendance-qr-state attendance-qr-state-warning">
                                <AlertCircle size={24} />
                                <strong>This session is not open for check-in.</strong>
                                <p>Only an active session within its scheduled time window can display a QR Code.</p>
                            </div>
                        ) : qrQuery.isLoading && !qrData ? (
                            <div className="attendance-qr-state"><LoaderCircle className="workspace-spin" size={28} /><strong>Preparing secure QR Code…</strong></div>
                        ) : qrData && secondsRemaining > 0 ? (
                            <>
                                <div className="attendance-qr-code-wrap">
                                    <QRCodeSVG value={qrValue} size={280} level="H" includeMargin />
                                </div>
                                <div className="attendance-qr-countdown">
                                    <Clock3 size={17} />
                                    <span>Code expires in</span>
                                    <strong>{secondsRemaining}s</strong>
                                </div>
                                <p className="attendance-qr-refresh-note">A new QR Code is generated every 30 seconds. Each code remains valid for up to 60 seconds to allow for scanning and network delay.</p>
                            </>
                        ) : (
                            <div className="attendance-qr-state attendance-qr-state-warning">
                                <AlertCircle size={24} />
                                <strong>{qrQuery.isError ? "Unable to issue a QR Code." : "The current QR Code has expired."}</strong>
                                <p>{qrQuery.error instanceof Error ? qrQuery.error.message : "A fresh code will be requested automatically."}</p>
                                <button type="button" className="button button-outline" onClick={() => void qrQuery.refetch()}><RefreshCw size={15} /> Generate new code</button>
                            </div>
                        )}

                        {qrQuery.isError && qrData && secondsRemaining > 0 && (
                            <div className="workspace-alert workspace-alert-warning">The next QR Code could not be generated. The displayed code remains valid for {secondsRemaining} seconds.</div>
                        )}
                    </section>

                    <aside className="attendance-qr-instructions">
                        <span className="attendance-instruction-icon"><ShieldCheck size={22} /></span>
                        <h2>Student check-in instructions</h2>
                        <ol>
                            <li>Students must sign in to their own RollNexa account.</li>
                            <li>They open Attendance and select Scan QR Code, or use their phone camera app.</li>
                            <li>They scan the code displayed on this screen; the RollNexa link opens the verification page.</li>
                            <li>RollNexa validates the session, token and course registration.</li>
                        </ol>
                        <div className="attendance-qr-policy-note">
                            <strong>Dual verification remains mandatory.</strong>
                            <p>This release verifies the QR stage only. Facial recognition must also succeed before a present attendance record can be created. Scanning this code alone does not mark a student present.</p>
                        </div>
                        <div className="attendance-qr-session-meta">
                            <div><span>Programme</span><strong>{session.programme_name}</strong></div>
                            <div><span>Academic session</span><strong>{session.academic_session}</strong></div>
                            <div><span>Semester</span><strong>{session.semester_name}</strong></div>
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}

function extractQrToken(value: string): string | null {
    const candidate = value.trim();
    if (/^[A-Za-z0-9_-]{32,512}$/.test(candidate)) {
        return candidate;
    }

    try {
        const parsed = new URL(candidate);
        if (
            parsed.origin !== window.location.origin
            || parsed.pathname !== "/app/attendance/check-in"
        ) {
            return null;
        }
        return parsed.searchParams.get("token");
    } catch {
        return null;
    }
}

export function AttendanceScanPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const initialToken = useRef(searchParams.get("token"));
    const processingRef = useRef(false);
    const cameraRequestedRef = useRef(false);
    const [scannerEnabled, setScannerEnabled] = useState(false);
    const [cameraError, setCameraError] = useState("");
    const [scanError, setScanError] = useState("");

    const verificationMutation = useMutation({
        mutationFn: (token: string) => apiRequest<VerificationResponse>("/api/v1/attendance/verify-qr/", {
            method: "POST",
            body: JSON.stringify({ token }),
        }),
        gcTime: 0,
        onSuccess: () => {
            setCameraError("");
            setScanError("");
            setScannerEnabled(false);
        },
        onError: (error) => {
            processingRef.current = false;
            setScanError(error instanceof Error ? error.message : "The QR Code could not be verified.");
            setScannerEnabled(cameraRequestedRef.current);
        },
    });

    const submitToken = useCallback((token: string) => {
        if (processingRef.current) return;
        processingRef.current = true;
        setScannerEnabled(false);
        setCameraError("");
        setScanError("");
        verificationMutation.mutate(token);
    }, [verificationMutation.mutate]);

    useEffect(() => {
        if (user?.role !== "student") return;
        const token = initialToken.current;
        if (!token) return;
        initialToken.current = null;
        navigate("/app/attendance/check-in", { replace: true });
        submitToken(token);
    }, [navigate, submitToken, user?.role]);

    useEffect(() => {
        if (user?.role !== "student" || !scannerEnabled || verificationMutation.isSuccess) return;

        const elementId = "rollnexa-qr-reader";
        const scanner = new Html5Qrcode(elementId, {
            formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
            verbose: false,
        });
        let disposed = false;

        scanner.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: { width: 250, height: 250 }, aspectRatio: 1 },
            (decodedText) => {
                const token = extractQrToken(decodedText);
                if (!token) {
                    setScanError("This is not a valid RollNexa attendance QR Code.");
                    return;
                }
                submitToken(token);
            },
            () => undefined,
        ).then(() => {
            if (disposed && scanner.isScanning) {
                return scanner.stop().then(() => scanner.clear());
            }
            return undefined;
        }).catch((error: unknown) => {
            if (!disposed) {
                setCameraError(error instanceof Error ? error.message : "The camera could not be started. Check browser permissions and try again.");
                setScannerEnabled(false);
            }
        });

        return () => {
            disposed = true;
            if (scanner.isScanning) {
                void scanner.stop().then(() => scanner.clear()).catch(() => undefined);
            } else {
                try {
                    scanner.clear();
                } catch {
                    // The scanner may not have completed initialisation.
                }
            }
        };
    }, [scannerEnabled, submitToken, user?.role, verificationMutation.isSuccess]);

    if (user?.role !== "student") {
        return <Navigate to="/app/attendance" replace />;
    }

    const verification = verificationMutation.data;

    return (
        <div className="dashboard-page attendance-scan-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div>
                    <span className="eyebrow">STUDENT WORKSPACE</span>
                    <h1>Scan attendance QR Code</h1>
                    <p>Scan the current code displayed by your lecturer to complete the first verification stage.</p>
                </div>
                <span className="release-chip"><span /> ROLLNEXA 1.0.0</span>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance</Link>

            {verification ? (
                <section className="attendance-verification-result">
                    <span className="attendance-result-icon"><CheckCircle2 size={30} /></span>
                    <span className="eyebrow">QR VERIFICATION SUCCESSFUL</span>
                    <h2>{verification.session.courseCode} — {verification.session.courseTitle}</h2>
                    <p>{verification.session.title} · {verification.session.academicSession} · {verification.session.semester}</p>
                    <div className="attendance-result-status"><ShieldCheck size={19} /><strong>{verification.alreadyVerified ? "Your QR verification is already active" : "First verification stage completed"}</strong></div>
                    <div className="attendance-qr-policy-note">
                        <strong>Attendance has not yet been recorded.</strong>
                        <p>Facial recognition must also verify your identity. RollNexa will only create a present record after both checks succeed. Your QR verification is valid until {new Date(verification.expiresAt).toLocaleTimeString()}.</p>
                    </div>
                    <div className="attendance-result-actions">
                        <Link to={`/app/attendance/face-check/${verification.verificationId}`} className="button button-primary"><ShieldCheck size={15} /> Continue to facial verification</Link>
                        <Link to="/app/history" className="button button-outline">View attendance history</Link>
                        <button type="button" className="button button-outline" onClick={() => { verificationMutation.reset(); processingRef.current = false; cameraRequestedRef.current = true; setScannerEnabled(true); }}>Scan another code</button>
                    </div>
                </section>
            ) : (
                <div className="attendance-scan-layout">
                    <section className="attendance-scanner-card">
                        <div className="attendance-scanner-heading"><span><Camera size={20} /></span><div><h2>Camera scanner</h2><p>Allow camera access and position the QR Code inside the scanning frame.</p></div></div>
                        <div id="rollnexa-qr-reader" className="attendance-qr-reader" />
                        {verificationMutation.isPending && <div className="workspace-alert workspace-alert-info"><LoaderCircle className="workspace-spin" size={17} /> Verifying your QR Code…</div>}
                        {cameraError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{cameraError}</div>}
                        {scanError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{scanError}</div>}
                        {!scannerEnabled && !verificationMutation.isPending && <button type="button" className="button button-outline" onClick={() => { cameraRequestedRef.current = true; setCameraError(""); setScannerEnabled(true); }}><Camera size={15} /> {cameraError ? "Try camera again" : "Start camera scanner"}</button>}
                    </section>
                    <aside className="attendance-scan-guidance">
                        <span className="attendance-instruction-icon"><ShieldCheck size={22} /></span>
                        <h2>Before you scan</h2>
                        <ul>
                            <li>Sign in with your own active student account.</li>
                            <li>Confirm that you are registered for the course.</li>
                            <li>Scan the QR Code currently displayed by your lecturer.</li>
                            <li>Keep the page open for the next verification stage.</li>
                        </ul>
                        <div className="attendance-qr-policy-note">
                            <strong>Two checks are mandatory.</strong>
                            <p>QR verification alone cannot mark you present. Facial recognition is required as the second check.</p>
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}
