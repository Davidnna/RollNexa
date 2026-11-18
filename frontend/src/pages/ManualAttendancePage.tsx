import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, CheckCircle2, ClipboardCheck, LoaderCircle, ShieldCheck } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";

interface SessionResponse {
    item: {
        id: number;
        offering_id: number;
        course_code: string;
        course_title: string;
        programme_name: string;
        title: string;
        status: string;
        is_open: boolean;
        academic_session: string;
        semester_name: string;
    };
}

interface RosterResponse {
    results: Array<{
        id: number;
        username: string;
        name: string;
        email: string;
        institutional_id: string;
        programme: string;
        level: string;
    }>;
}

interface ManualRecordsResponse {
    alreadyRecordedStudentIds: number[];
    manualRecords: Array<{
        id: number;
        studentId: number;
        studentName: string;
        institutionalId: string;
        reason: string;
        notes: string;
        recordedAt: string;
    }>;
}

const reasonOptions = [
    { value: "consent_withdrawn", label: "Biometric consent not given or withdrawn" },
    { value: "camera_unavailable", label: "Camera unavailable" },
    { value: "accessibility", label: "Accessibility accommodation" },
    { value: "recognition_failed", label: "Facial verification unsuccessful" },
    { value: "technical_issue", label: "Technical issue" },
    { value: "other", label: "Other approved reason" },
];

export function ManualAttendancePage() {
    const { user } = useAuth();
    const { sessionId = "" } = useParams();
    const queryClient = useQueryClient();
    const [studentId, setStudentId] = useState("");
    const [reason, setReason] = useState("consent_withdrawn");
    const [notes, setNotes] = useState("");
    const [pageError, setPageError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    const sessionQuery = useQuery({
        queryKey: ["workspace", "attendance-session", sessionId],
        queryFn: () => apiRequest<SessionResponse>(`/api/v1/workspace/attendance-sessions/${sessionId}/`),
        enabled: Boolean(sessionId),
    });
    const offeringId = sessionQuery.data?.item.offering_id;
    const rosterQuery = useQuery({
        queryKey: ["workspace", "roster", offeringId],
        queryFn: () => apiRequest<RosterResponse>(`/api/v1/workspace/rosters/?offering=${offeringId}&page_size=100`),
        enabled: Boolean(offeringId),
    });
    const recordsQuery = useQuery({
        queryKey: ["attendance", "manual-records", sessionId],
        queryFn: () => apiRequest<ManualRecordsResponse>(`/api/v1/attendance/sessions/${sessionId}/manual-records/`),
        enabled: Boolean(sessionId),
    });
    const recordMutation = useMutation({
        mutationFn: () => apiRequest<{ detail: string }>(`/api/v1/attendance/sessions/${sessionId}/manual-records/`, {
            method: "POST",
            body: JSON.stringify({ studentId, reason, notes }),
        }),
        onSuccess: async (response) => {
            setPageError("");
            setSuccessMessage(response.detail);
            setStudentId("");
            setNotes("");
            await queryClient.invalidateQueries({ queryKey: ["attendance", "manual-records", sessionId] });
            await queryClient.invalidateQueries({ queryKey: ["workspace"] });
            await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        },
        onError: (error) => {
            setSuccessMessage("");
            setPageError(error instanceof Error ? error.message : "The manual attendance exception could not be recorded.");
        },
    });

    const recordedIds = useMemo(() => new Set(recordsQuery.data?.alreadyRecordedStudentIds ?? []), [recordsQuery.data]);
    const eligibleStudents = (rosterQuery.data?.results ?? []).filter((student) => !recordedIds.has(student.id));
    const session = sessionQuery.data?.item;

    if (user?.role !== "lecturer") return <Navigate to="/app" replace />;

    function submitManualRecord(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setPageError("");
        setSuccessMessage("");
        if (!studentId) {
            setPageError("Select a registered student.");
            return;
        }
        if (reason === "other" && !notes.trim()) {
            setPageError("Provide an explanation when selecting Other.");
            return;
        }
        if (!window.confirm("Confirm that you are approving an alternative manual attendance record for this student?")) return;
        recordMutation.mutate();
    }

    return (
        <div className="dashboard-page biometric-page manual-attendance-page">
            <div className="dashboard-page-heading workspace-page-heading">
                <div><span className="eyebrow">LECTURER WORKSPACE</span><h1>Manual attendance exception</h1><p>Record an approved alternative when a student cannot complete biometric verification.</p></div>
                <span className="release-chip"><span /> ROLLNEXA 1.0.5</span>
            </div>
            <Link to="/app/attendance" className="attendance-back-link"><ArrowLeft size={16} /> Back to attendance sessions</Link>

            {pageError && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{pageError}</div>}
            {successMessage && <div className="workspace-alert workspace-alert-success"><CheckCircle2 size={17} />{successMessage}</div>}
            {(sessionQuery.isLoading || rosterQuery.isLoading || recordsQuery.isLoading) && <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading class information…</div>}
            {(sessionQuery.isError || rosterQuery.isError || recordsQuery.isError) && <div className="workspace-alert workspace-alert-error">The attendance session or class roster could not be loaded. Confirm that this session belongs to one of your active teaching assignments.</div>}

            {session && (
                <>
                    <section className="biometric-status-card">
                        <div className="biometric-status-icon"><ClipboardCheck size={24} /></div>
                        <div className="biometric-status-copy"><span className="eyebrow">ATTENDANCE SESSION</span><h2>{session.course_code} · {session.title || "Attendance session"}</h2><p>{session.course_title} · {session.programme_name} · {session.academic_session} · {session.semester_name}</p></div>
                        <span className={`workspace-status ${session.is_open ? "is-positive" : "is-neutral"}`}>{session.is_open ? "Open" : session.status}</span>
                    </section>
                    {!session.is_open && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />Manual attendance can only be approved while this attendance session is active and within its scheduled time window.</div>}
                    <section className="biometric-panel">
                        <span className="eyebrow">LECTURER-APPROVED ALTERNATIVE</span>
                        <h2>Record a student's attendance</h2>
                        <p>This creates a present record labelled as a manual exception. It does not represent successful QR Code or facial verification.</p>
                        <form className="manual-attendance-form" onSubmit={submitManualRecord}>
                            <label className="workspace-form-field"><span>Registered student</span><select value={studentId} onChange={(event) => setStudentId(event.target.value)} required><option value="">Select a student</option>{eligibleStudents.map((student) => <option key={student.id} value={student.id}>{student.name} · {student.institutional_id || student.username}</option>)}</select></label>
                            <label className="workspace-form-field"><span>Reason for exception</span><select value={reason} onChange={(event) => setReason(event.target.value)}>{reasonOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
                            <label className="workspace-form-field"><span>Additional notes {reason === "other" ? "(required)" : "(optional)"}</span><textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record a brief explanation for the audit trail." /></label>
                            <button className="button button-primary" type="submit" disabled={!session.is_open || !eligibleStudents.length || recordMutation.isPending}>{recordMutation.isPending ? <LoaderCircle size={15} className="workspace-spin" /> : <ShieldCheck size={15} />} Approve manual attendance</button>
                            {!eligibleStudents.length && <p className="workspace-form-hint">All registered students already have an attendance record, or no students are currently registered.</p>}
                        </form>
                    </section>
                    <section className="biometric-panel">
                        <span className="eyebrow">AUDIT HISTORY</span>
                        <h2>Manual exceptions recorded for this session</h2>
                        {!recordsQuery.data?.manualRecords.length ? <p>No manual attendance exceptions have been recorded for this session.</p> : (
                            <div className="workspace-table-scroll"><table className="workspace-data-table"><thead><tr><th>Student</th><th>Institutional ID</th><th>Reason</th><th>Recorded at</th></tr></thead><tbody>{recordsQuery.data.manualRecords.map((record) => <tr key={record.id}><td>{record.studentName}</td><td>{record.institutionalId || "—"}</td><td>{record.reason}</td><td>{new Date(record.recordedAt).toLocaleString()}</td></tr>)}</tbody></table></div>
                        )}
                    </section>
                </>
            )}
        </div>
    );
}
