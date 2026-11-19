import { useCallback, useEffect, useRef, useState } from "react";
import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, Camera, Clock3, LoaderCircle, QrCode, RefreshCw, ShieldCheck } from "lucide-react";
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
                    <h1>Class check-in code</h1>
                    <p>Display this code for students in the selected course.</p>
                </div>
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
                                <p className="attendance-qr-refresh-note">The code refreshes automatically. Students should scan the current code.</p>
                            </>
                        ) : (
                            <div className="attendance-qr-state attendance-qr-state-warning">
                                <AlertCircle size={24} />
                                <strong>{qrQuery.isError ? "Unable to issue a QR Code." : "This code has expired."}</strong>
                                <p>{qrQuery.error instanceof Error ? qrQuery.error.message : "A fresh code will be requested automatically."}</p>
                                <button type="button" className="button button-outline" onClick={() => void qrQuery.refetch()}><RefreshCw size={15} /> Refresh code</button>
                            </div>
                        )}

                        {qrQuery.isError && qrData && secondsRemaining > 0 && (
                            <div className="workspace-alert workspace-alert-warning">The next QR Code could not be generated. The displayed code remains valid for {secondsRemaining} seconds.</div>
                        )}
                    </section>

                    <aside className="attendance-qr-instructions">
                        <span className="attendance-instruction-icon"><ShieldCheck size={22} /></span>
                        <h2>For students</h2>
                        <p>Students sign in to RollNexa and scan this code. They then follow the face check to complete attendance.</p>
                        <div className="attendance-qr-policy-note">
                            <strong>Attendance check-in</strong>
                            <p>Attendance is recorded after the face check is complete.</p>
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
            setScanError(error instanceof Error ? error.message : "This class code could not be verified.");
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
        const verified = verificationMutation.data;
        if (!verified) return;
        navigate(`/app/attendance/face-check/${verified.verificationId}`, { replace: true });
    }, [verificationMutation.data, navigate]);

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
                    setScanError("This is not a valid class code.");
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
                setCameraError(error instanceof Error ? error.message : "We could not open the camera. Check your browser permissions and try again.");
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
                    <h1>Scan class code</h1>
                    <p>Scan the code shown by your lecturer.</p>
                </div>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance</Link>

            {verification ? (
                <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Opening face check…</div>
            ) : (
                <div className="attendance-scan-layout">
                    <section className="attendance-scanner-card">
                        <div className="attendance-scanner-heading"><span><Camera size={20} /></span><div><h2>Scan the class code</h2><p>Allow camera access and point it at the class code.</p></div></div>
                        <div id="rollnexa-qr-reader" className="attendance-qr-reader" />
                        {verificationMutation.isPending && <div className="workspace-alert workspace-alert-info"><LoaderCircle className="workspace-spin" size={17} /> Checking the class code…</div>}
                        {cameraError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{cameraError}</div>}
                        {scanError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{scanError}</div>}
                        {!scannerEnabled && !verificationMutation.isPending && <button type="button" className="button button-outline" onClick={() => { cameraRequestedRef.current = true; setCameraError(""); setScannerEnabled(true); }}><Camera size={15} /> {cameraError ? "Try again" : "Open camera"}</button>}
                    </section>
                    <aside className="attendance-scan-guidance">
                        <span className="attendance-instruction-icon"><ShieldCheck size={22} /></span>
                        <h2>Need help?</h2>
                        <p>Sign in with your student account and scan the current code shown by your lecturer. Keep this page open until check-in is complete.</p>
                        <div className="attendance-qr-policy-note">
                            <strong>Two checks are mandatory.</strong>
                            <p>Your attendance is recorded after the face check is complete.</p>
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}
