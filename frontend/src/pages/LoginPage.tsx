import { useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const { isAuthenticated, isLoading, login, user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const requestedDestination = (location.state as { from?: string } | null)?.from
        ?? new URLSearchParams(location.search).get("next");
    const destination = requestedDestination?.startsWith("/") && !requestedDestination.startsWith("//")
        ? requestedDestination
        : "/app";

    if (isLoading) {
        return <div className="full-page-loading"><span className="loading-spinner" /> Checking your session…</div>;
    }

    if (isAuthenticated) {
        return <Navigate to={user?.mustChangePassword ? "/app/password-change" : destination} replace />;
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setSubmitting(true);

        try {
            const authenticatedUser = await login(username.trim(), password);
            if (authenticatedUser.mustChangePassword) {
                navigate("/app/password-change", { replace: true });
            } else if (destination === "/app" || destination.startsWith("/app/")) {
                navigate(destination, { replace: true });
            } else {
                window.location.assign(destination);
            }
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : "Unable to sign in. Check your details and try again.");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="login-page">
            <div className="login-side-panel">
                <Link to="/" className="login-back-link"><ArrowLeft size={16} /> Back to RollNexa</Link>
                <div className="login-side-content">
                    <span className="login-side-kicker">ROLLNEXA WORKSPACE</span>
                    <h1>Academic workflows, <span>connected.</span></h1>
                    <p>Sign in to access your role-based workspace for academic administration and attendance management.</p>
                    <div className="login-side-points">
                        <div><ShieldCheck size={18} /><span>Secure, role-based access</span></div>
                        <div><LockKeyhole size={18} /><span>Protected account sessions</span></div>
                    </div>
                </div>
                <div className="login-side-footer">Attendance, connected.</div>
            </div>
            <div className="login-form-panel">
                <div className="login-form-wrap">
                    <Link to="/" className="login-mobile-brand"><img src="/static/images/rollnexa-logo.svg" alt="RollNexa" /></Link>
                    <span className="eyebrow">WELCOME BACK</span>
                    <h2>Sign in to your account</h2>
                    <p className="login-form-description">Use the username and password provided by your institution.</p>
                    <form className="login-form" onSubmit={handleSubmit}>
                        {error && <div className="form-alert form-alert-error" role="alert">{error}</div>}
                        <label htmlFor="username">Username</label>
                        <input
                            id="username"
                            type="text"
                            autoComplete="username"
                            autoFocus
                            value={username}
                            onChange={(event) => setUsername(event.target.value)}
                            placeholder="Enter your username"
                            required
                        />
                        <label htmlFor="password">Password</label>
                        <div className="password-input-wrap">
                            <input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="current-password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                placeholder="Enter your password"
                                required
                            />
                            <button type="button" className="password-visibility" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}>
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        <button className="button button-primary login-submit" type="submit" disabled={submitting}>
                            {submitting ? "Signing in…" : "Sign in securely"}
                            {!submitting && <ArrowRight size={17} />}
                        </button>
                    </form>
                    <div className="login-support-note"><ShieldCheck size={17} /><span>Access is provisioned by your institution. If you need an account or password assistance, contact your RollNexa administrator.</span></div>
                    <Link to="/" className="login-home-link">Return to public website</Link>
                </div>
            </div>
        </div>
    );
}
