import { useState, type FormEvent, type ReactNode } from "react";
import {
    Activity,
    ArrowRight,
    BookOpen,
    CheckCircle2,
    CircleAlert,
    ClipboardCheck,
    GraduationCap,
    LockKeyhole,
    RefreshCw,
    ShieldCheck,
    Users,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";

interface DashboardCard {
    key: string;
    label: string;
    value: number;
    description: string;
}

interface DashboardSummary {
    role: string;
    cards: DashboardCard[];
    academic?: Record<string, number>;
    recentUsers?: Array<{
        id: number;
        name: string;
        username: string;
        role: string;
        joinedAt: string;
        isActive: boolean;
    }>;
    courses?: Array<{
        id: number;
        code: string;
        title: string;
        programme: string;
        level: string;
        semester: string;
        academicSession: string;
    }>;
    attendance?: {
        verifiedRecords: number;
    };
}

export function DashboardHome() {
    const { user } = useAuth();
    const summaryQuery = useQuery({
        queryKey: ["dashboard", "summary"],
        queryFn: () => apiRequest<DashboardSummary>("/api/v1/dashboard/summary/"),
    });

    const greetingName = user?.firstName || user?.fullName || "there";

    return (
        <div className="dashboard-page">
            <div className="dashboard-page-heading">
                <div>
                    <span className="eyebrow">YOUR WORKSPACE</span>
                    <h1>Good day, {greetingName}.</h1>
                    <p>Here is an overview of the information available to your account.</p>
                </div>
                <span className="release-chip"><span /> ROLLNEXA 0.7.0</span>
            </div>

            {summaryQuery.isLoading && <div className="dashboard-loading"><span className="loading-spinner" /> Loading your workspace summary…</div>}
            {summaryQuery.isError && (
                <div className="inline-alert inline-alert-error">
                    <CircleAlert size={18} />
                    <span>{summaryQuery.error instanceof Error ? summaryQuery.error.message : "The dashboard summary could not be loaded."}</span>
                    <button onClick={() => void summaryQuery.refetch()}><RefreshCw size={15} /> Retry</button>
                </div>
            )}

            {summaryQuery.data && (
                <>
                    <div className="summary-card-grid">
                        {summaryQuery.data.cards.map((card, index) => {
                            const icons = [Users, BookOpen, ClipboardCheck, Activity];
                            const Icon = icons[index % icons.length];
                            return (
                                <article className="summary-card" key={card.key}>
                                    <div className="summary-card-top"><span>{card.label}</span><span className="summary-card-icon"><Icon size={18} /></span></div>
                                    <strong>{card.value.toLocaleString()}</strong>
                                    <small>{card.description}</small>
                                </article>
                            );
                        })}
                    </div>

                    {summaryQuery.data.academic && (
                        <section className="dashboard-panel">
                            <div className="panel-heading"><div><span className="eyebrow">INSTITUTIONAL OVERVIEW</span><h2>Academic structure</h2></div><Link to="/app/academic" className="panel-link">Manage structure <ArrowRight size={15} /></Link></div>
                            <div className="academic-stat-grid">
                                {Object.entries(summaryQuery.data.academic).map(([key, value]) => (
                                    <div className="academic-stat" key={key}><strong>{value.toLocaleString()}</strong><span>{formatLabel(key)}</span></div>
                                ))}
                            </div>
                        </section>
                    )}

                    {summaryQuery.data.recentUsers && (
                        <section className="dashboard-panel">
                            <div className="panel-heading"><div><span className="eyebrow">ACCOUNT ACTIVITY</span><h2>Recently added users</h2></div><Link to="/app/users" className="panel-link">View users <ArrowRight size={15} /></Link></div>
                            {summaryQuery.data.recentUsers.length ? (
                                <div className="responsive-table-wrap">
                                    <table className="data-table">
                                        <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Status</th></tr></thead>
                                        <tbody>
                                            {summaryQuery.data.recentUsers.map((item) => (
                                                <tr key={item.id}>
                                                    <td><strong>{item.name}</strong></td>
                                                    <td>{item.username}</td>
                                                    <td><span className="role-pill">{item.role}</span></td>
                                                    <td><span className={`account-status ${item.isActive ? "is-active" : "is-inactive"}`}>{item.isActive ? "Active" : "Inactive"}</span></td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <div className="empty-state">No user accounts have been added yet.</div>}
                        </section>
                    )}

                    {summaryQuery.data.courses && (
                        <section className="dashboard-panel">
                            <div className="panel-heading"><div><span className="eyebrow">{summaryQuery.data.role === "lecturer" ? "TEACHING ASSIGNMENTS" : "COURSE REGISTRATION"}</span><h2>{summaryQuery.data.role === "lecturer" ? "Your assigned courses" : "Your registered courses"}</h2></div><Link to="/app/courses" className="panel-link">View courses <ArrowRight size={15} /></Link></div>
                            {summaryQuery.data.courses.length ? (
                                <div className="course-preview-grid">
                                    {summaryQuery.data.courses.map((course) => (
                                        <article className="course-preview-card" key={course.id}>
                                            <span className="course-code">{course.code}</span>
                                            <h3>{course.title}</h3>
                                            <p>{course.programme}</p>
                                            <div className="course-preview-meta"><span>{course.level} level</span><span>{course.semester}</span></div>
                                            <small>{course.academicSession}</small>
                                        </article>
                                    ))}
                                </div>
                            ) : <div className="empty-state">No active course assignments are currently associated with your account.</div>}
                        </section>
                    )}

                    {summaryQuery.data.attendance && (
                        <section className="dashboard-panel student-attendance-panel">
                            <div className="student-attendance-icon"><CheckCircle2 size={23} /></div>
                            <div><span className="eyebrow">ATTENDANCE RECORDS</span><h2>{summaryQuery.data.attendance.verifiedRecords} verified attendance records</h2><p>Attendance history will be available in your student workspace as the reporting module is introduced.</p></div>
                        </section>
                    )}
                </>
            )}

            <section className="dashboard-release-note">
                <div className="release-note-icon"><GraduationCap size={20} /></div>
                <div><strong>Your RollNexa workspace is moving to React.</strong><p>The new interface is being introduced in stages. Existing academic management screens remain available while their workflows are migrated.</p></div>
                <Link to="/features">Release information <ArrowRight size={15} /></Link>
            </section>
        </div>
    );
}

function formatLabel(value: string): string {
    return value.replace(/([A-Z])/g, " $1").replace(/^./, (character) => character.toUpperCase());
}

interface LegacyDestination {
    title: string;
    description: string;
    legacyPath?: string;
    legacyLabel?: string;
}

const workspaceDestinations: Record<string, Record<string, LegacyDestination>> = {
    admin: {
        users: { title: "User management", description: "Manage student and lecturer accounts, account status and institutional profiles.", legacyPath: "/management/users/", legacyLabel: "Open existing user management" },
        academic: { title: "Academic structure", description: "Manage faculties, departments, programmes, academic sessions and semesters.", legacyPath: "/management/academic/", legacyLabel: "Open existing academic management" },
        courses: { title: "Course management", description: "Manage the course catalogue, course offerings, lecturer assignments and registrations.", legacyPath: "/management/courses/", legacyLabel: "Open existing course management" },
        attendance: { title: "Attendance oversight", description: "The React attendance administration workspace is scheduled for a later migration release." },
        reports: { title: "Reports and analytics", description: "Institution-wide attendance reports and analytics will be introduced after the attendance verification workflow is operational." },
        settings: { title: "System settings", description: "Account and platform settings will be migrated into the React workspace in a subsequent release." },
    },
    lecturer: {
        courses: { title: "My courses", description: "Review your active teaching assignments and course offerings.", legacyPath: "/lecturer/courses/", legacyLabel: "Open existing lecturer courses" },
        rosters: { title: "Class rosters", description: "Review the students registered for your assigned course offerings.", legacyPath: "/lecturer/courses/", legacyLabel: "Open existing class rosters" },
        attendance: { title: "Attendance sessions", description: "Schedule, activate and manage attendance sessions for your assigned courses.", legacyPath: "/lecturer/attendance/", legacyLabel: "Open existing attendance sessions" },
        reports: { title: "Attendance reports", description: "Attendance summaries and exports will be introduced after QR and facial verification are integrated." },
        profile: { title: "My profile", description: "Profile management will be migrated into the React workspace in a subsequent release." },
    },
    student: {
        courses: { title: "My courses", description: "View registered courses and manage course registration where registration is open.", legacyPath: "/student/courses/", legacyLabel: "Open existing student courses" },
        attendance: { title: "Attendance check-in", description: "Student attendance check-in will be enabled after QR Code and facial verification have both been implemented and tested." },
        history: { title: "Attendance history", description: "Verified attendance history and attendance summaries will be introduced in a later release." },
        profile: { title: "My profile", description: "Profile management will be migrated into the React workspace in a subsequent release." },
    },
};

export function WorkspacePage() {
    const { user } = useAuth();
    const location = useLocation();
    const section = location.pathname.split("/")[2] ?? "overview";
    const destination = workspaceDestinations[user?.role ?? "student"]?.[section] ?? {
        title: "Workspace module",
        description: "This module is part of the staged RollNexa interface migration.",
    };

    return (
        <div className="dashboard-page">
            <div className="dashboard-page-heading">
                <div><span className="eyebrow">WORKSPACE MODULE</span><h1>{destination.title}</h1><p>{destination.description}</p></div>
            </div>
            <div className="migration-card">
                <span className="migration-icon"><Activity size={23} /></span>
                <span className="status-tag status-planned">React migration in progress</span>
                <h2>This workspace is being introduced in stages.</h2>
                <p>RollNexa 0.7.0 establishes the React application, secure authentication and dashboard foundation. Existing Django workflows remain available during the migration so that current institutional operations are not interrupted.</p>
                {destination.legacyPath ? (
                    <a className="button button-primary" href={destination.legacyPath}>{destination.legacyLabel} <ArrowRight size={16} /></a>
                ) : (
                    <Link className="button button-outline" to="/features">Review platform capabilities <ArrowRight size={16} /></Link>
                )}
            </div>
        </div>
    );
}

export function PasswordChangePage() {
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const { refreshSession, user } = useAuth();
    const navigate = useNavigate();

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setSuccess("");
        setSubmitting(true);

        try {
            const response = await apiRequest<{ detail: string }>("/api/v1/auth/password-change/", {
                method: "POST",
                body: JSON.stringify({ currentPassword, newPassword, confirmPassword }),
            });
            setSuccess(response.detail);
            await refreshSession();
            window.setTimeout(() => navigate("/app", { replace: true }), 700);
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : "Your password could not be changed.");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="dashboard-page narrow-dashboard-page">
            <div className="dashboard-page-heading"><div><span className="eyebrow">ACCOUNT SECURITY</span><h1>Change your password</h1><p>Choose a strong password that you do not use for another account.</p></div></div>
            {user?.mustChangePassword && <div className="inline-alert inline-alert-info"><LockKeyhole size={18} /> Your administrator issued a temporary password. You must change it before continuing.</div>}
            <form className="password-form-card" onSubmit={handleSubmit}>
                {error && <div className="form-alert form-alert-error">{error}</div>}
                {success && <div className="form-alert form-alert-success">{success}</div>}
                <label>Current password<input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
                <label>New password<input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} /></label>
                <label>Confirm new password<input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={8} /></label>
                <div className="password-form-hint"><ShieldCheck size={16} /> Your password is validated against the platform's configured password rules.</div>
                <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? "Updating password…" : "Update password"} <ArrowRight size={16} /></button>
            </form>
        </div>
    );
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();

    if (isLoading) {
        return <div className="full-page-loading"><span className="loading-spinner" /> Checking your session…</div>;
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    }

    if (user?.mustChangePassword && location.pathname !== "/app/password-change") {
        return <Navigate to="/app/password-change" replace />;
    }

    return children;
}
