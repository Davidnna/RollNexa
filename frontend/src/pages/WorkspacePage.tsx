import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
    AlertCircle,
    ArrowRight,
    BookOpen,
    Check,
    ChevronLeft,
    ChevronRight,
    ClipboardList,
    Edit3,
    Filter,
    LoaderCircle,
    Plus,
    RefreshCw,
    Search,
    ShieldCheck,
    UserRound,
    X,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";

type Row = Record<string, unknown>;
type Choice = { value: string | number; label: string };
type FieldType = "text" | "email" | "number" | "date" | "datetime-local" | "textarea" | "select" | "checkbox";

interface FieldSpec {
    name: string;
    label: string;
    type?: FieldType;
    required?: boolean;
    options?: Choice[];
    optionKey?: string;
    createOnly?: boolean;
    editOnly?: boolean;
    visibleWhen?: (values: Row) => boolean;
    help?: string;
}

interface ResourceConfig {
    resource: string;
    title: string;
    description: string;
    columns: Array<{ key: string; label: string }>;
    fields?: FieldSpec[];
    createLabel?: string;
    readOnly?: boolean;
    emptyText?: string;
}

interface WorkspaceResponse {
    results: Row[];
    count: number;
    page: number;
    pageSize: number;
    pages: number;
    hasNext: boolean;
    hasPrevious: boolean;
    options?: Record<string, Choice[]>;
    profileComplete?: boolean;
}

interface ReportsResponse {
    role: string;
    attendance: Record<string, number>;
    academic?: Record<string, number>;
    recentSessions: Row[];
    notice?: string;
}

const levels: Choice[] = [100, 200, 300, 400, 500, 600, 700].map((level) => ({
    value: String(level),
    label: `${level} level`,
}));

const stressCodes: Choice[] = [
    { value: "", label: "Not specified" },
    { value: "C", label: "Core (C)" },
    { value: "R", label: "Required (R)" },
    { value: "E", label: "Elective (E)" },
    { value: "G", label: "General (G)" },
    { value: "AR", label: "As published: AR" },
];

const academicTabs = [
    { resource: "faculties", label: "Faculties" },
    { resource: "departments", label: "Departments" },
    { resource: "programmes", label: "Programmes" },
    { resource: "sessions", label: "Academic sessions" },
    { resource: "semesters", label: "Semesters" },
];

const courseTabs = [
    { resource: "courses", label: "Course catalogue" },
    { resource: "offerings", label: "Course offerings" },
    { resource: "assignments", label: "Teaching assignments" },
];

function getResourceConfig(resource: string, role: string): ResourceConfig {
    const configs: Record<string, ResourceConfig> = {
        users: {
            resource,
            title: "User management",
            description: "Create, update and manage lecturer and student accounts. New accounts receive a temporary password that must be changed at first sign-in.",
            createLabel: "Create account",
            columns: [
                { key: "full_name", label: "Name" },
                { key: "username", label: "Username" },
                { key: "email", label: "Email" },
                { key: "role", label: "Role" },
                { key: "institutional_id", label: "Institutional ID" },
                { key: "department_name", label: "Department" },
                { key: "programme_name", label: "Programme" },
                { key: "is_active", label: "Status" },
            ],
            fields: [
                { name: "username", label: "Username", required: true, createOnly: true },
                { name: "first_name", label: "First name", required: true },
                { name: "last_name", label: "Last name", required: true },
                { name: "email", label: "Email address", type: "email", required: true },
                { name: "role", label: "Account role", type: "select", required: true, createOnly: true, options: [
                    { value: "student", label: "Student" },
                    { value: "lecturer", label: "Lecturer" },
                ] },
                { name: "institutional_id", label: "Institutional ID" },
                { name: "phone_number", label: "Phone number" },
                { name: "department", label: "Department", type: "select", optionKey: "departments", visibleWhen: (values) => values.role === "lecturer" },
                { name: "programme", label: "Programme", type: "select", optionKey: "programmes", visibleWhen: (values) => values.role === "student" },
                { name: "current_level", label: "Current level", type: "select", options: [{ value: "", label: "Select level" }, ...levels], visibleWhen: (values) => values.role === "student" },
            ],
        },
        faculties: {
            resource, title: "Faculties", description: "Manage the top-level institutional academic units.", createLabel: "Add faculty",
            columns: [{ key: "code", label: "Code" }, { key: "name", label: "Faculty" }, { key: "department_count", label: "Departments" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "code", label: "Faculty code", required: true }, { name: "name", label: "Faculty name", required: true }, { name: "description", label: "Description", type: "textarea" }],
        },
        departments: {
            resource, title: "Departments", description: "Manage departments and their parent faculties.", createLabel: "Add department",
            columns: [{ key: "code", label: "Code" }, { key: "name", label: "Department" }, { key: "faculty_name", label: "Faculty" }, { key: "programme_count", label: "Programmes" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "faculty", label: "Faculty", type: "select", optionKey: "faculties", required: true }, { name: "code", label: "Department code", required: true }, { name: "name", label: "Department name", required: true }, { name: "description", label: "Description", type: "textarea" }],
        },
        programmes: {
            resource, title: "Programmes", description: "Configure programmes, awards, duration and study mode.", createLabel: "Add programme",
            columns: [{ key: "code", label: "Code" }, { key: "name", label: "Programme" }, { key: "department_name", label: "Department" }, { key: "award", label: "Award" }, { key: "mode", label: "Mode" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "department", label: "Department", type: "select", optionKey: "departments", required: true }, { name: "code", label: "Programme code", required: true }, { name: "name", label: "Programme name", required: true }, { name: "award", label: "Award" }, { name: "duration_years", label: "Duration (years)", type: "number" }, { name: "mode", label: "Study mode", type: "select", required: true, options: [{ value: "full_time", label: "Full-time" }, { value: "part_time", label: "Part-time" }] }, { name: "description", label: "Description", type: "textarea" }],
        },
        sessions: {
            resource, title: "Academic sessions", description: "Manage academic years and designate the current session.", createLabel: "Add academic session",
            columns: [{ key: "name", label: "Session" }, { key: "start_date", label: "Starts" }, { key: "end_date", label: "Ends" }, { key: "is_current", label: "Current" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "name", label: "Session (YYYY/YYYY)", required: true }, { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" }],
        },
        semesters: {
            resource, title: "Semesters", description: "Manage semesters within academic sessions and select the current semester.", createLabel: "Add semester",
            columns: [{ key: "name_display", label: "Semester" }, { key: "session_name", label: "Academic session" }, { key: "start_date", label: "Starts" }, { key: "end_date", label: "Ends" }, { key: "is_current", label: "Current" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "session", label: "Academic session", type: "select", optionKey: "sessions", required: true }, { name: "name", label: "Semester", type: "select", required: true, options: [{ value: "first", label: "First semester" }, { value: "second", label: "Second semester" }, { value: "summer", label: "Summer semester" }] }, { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" }],
        },
        courses: {
            resource, title: role === "admin" ? "Course catalogue" : "My courses", description: role === "admin" ? "Maintain the master course catalogue and departmental ownership." : "Review your active teaching assignments and the course offerings you teach.",
            createLabel: "Add course",
            columns: role === "admin" ? [
                { key: "code", label: "Code" }, { key: "title", label: "Course" }, { key: "department_name", label: "Department" }, { key: "credit_units", label: "Units" }, { key: "is_active", label: "Status" },
            ] : [
                { key: "code", label: "Code" }, { key: "course_title", label: "Course" }, { key: "programme_name", label: "Programme" }, { key: "level", label: "Level" }, { key: "semester_name", label: "Semester" }, { key: "academic_session", label: "Session" },
            ],
            fields: role === "admin" ? [
                { name: "department", label: "Department", type: "select", optionKey: "departments", required: true }, { name: "code", label: "Course code", required: true }, { name: "title", label: "Course title", required: true }, { name: "credit_units", label: "Catalogue credit units", type: "number", required: true }, { name: "stress_code", label: "Classification", type: "select", options: stressCodes }, { name: "description", label: "Description", type: "textarea" },
            ] : undefined,
            readOnly: role !== "admin",
        },
        offerings: {
            resource, title: "Course offerings", description: "Deliver catalogue courses to programmes, levels and academic semesters. Registration capacity and opening status are managed per offering.", createLabel: "Create offering",
            columns: [{ key: "course_code", label: "Course" }, { key: "course_title", label: "Title" }, { key: "programme_name", label: "Programme" }, { key: "level", label: "Level" }, { key: "semester_name", label: "Semester" }, { key: "academic_session", label: "Session" }, { key: "registered_count", label: "Registered" }, { key: "registration_open", label: "Registration" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "course", label: "Course", type: "select", optionKey: "courses", required: true }, { name: "programme", label: "Programme", type: "select", optionKey: "programmes", required: true }, { name: "semester", label: "Semester", type: "select", optionKey: "semesters", required: true }, { name: "level", label: "Level", type: "select", options: levels, required: true }, { name: "credit_units", label: "Approved credit units", type: "number", required: true }, { name: "stress_code", label: "Classification", type: "select", options: stressCodes }, { name: "source_url", label: "Curriculum source URL", type: "text" }, { name: "source_note", label: "Source note", type: "textarea" }, { name: "max_students", label: "Maximum students", type: "number" }, { name: "registration_open", label: "Open student registration", type: "checkbox" }, { name: "notes", label: "Notes", type: "textarea" }],
        },
        assignments: {
            resource, title: "Teaching assignments", description: "Assign active lecturers to course offerings. Cross-department teaching assignments are permitted and retain the lecturer's home department.", createLabel: "Assign lecturer",
            columns: [{ key: "lecturer_name", label: "Lecturer" }, { key: "lecturer_department", label: "Home department" }, { key: "course_code", label: "Course" }, { key: "programme_name", label: "Programme" }, { key: "academic_session", label: "Session" }, { key: "is_cross_department", label: "Cross-department" }, { key: "is_active", label: "Status" }],
            fields: [{ name: "offering", label: "Course offering", type: "select", optionKey: "offerings", required: true }, { name: "lecturer", label: "Lecturer", type: "select", optionKey: "lecturers", required: true }],
        },
        "lecturer-courses": {
            resource, title: "My courses", description: "Review your active teaching assignments and open a class roster for a course offering.",
            columns: [{ key: "course_code", label: "Code" }, { key: "course_title", label: "Course" }, { key: "programme_name", label: "Programme" }, { key: "level", label: "Level" }, { key: "semester_name", label: "Semester" }, { key: "academic_session", label: "Session" }, { key: "registered_count", label: "Registered" }],
            readOnly: true,
        },
        "student-courses": {
            resource, title: "Course registration", description: "Review course offerings available to your assigned programme and level. Registration and withdrawal are controlled by the academic offering settings.",
            columns: [{ key: "course_code", label: "Code" }, { key: "course_title", label: "Course" }, { key: "programme_name", label: "Programme" }, { key: "level", label: "Level" }, { key: "semester_name", label: "Semester" }, { key: "academic_session", label: "Session" }, { key: "credit_units", label: "Units" }, { key: "registration_open", label: "Registration" }, { key: "is_registered", label: "My status" }],
            readOnly: true,
        },
        "attendance-sessions": {
            resource, title: "Attendance sessions", description: "Schedule and manage sessions for course offerings assigned to you. Attendance recording remains disabled until both QR Code and facial verification are operational.", createLabel: "Schedule session",
            columns: [{ key: "course_code", label: "Course" }, { key: "title", label: "Session title" }, { key: "programme_name", label: "Programme" }, { key: "starts_at", label: "Starts" }, { key: "ends_at", label: "Ends" }, { key: "status", label: "Status" }, { key: "registered_count", label: "Enrolled" }, { key: "attendance_count", label: "Present" }],
            fields: [{ name: "offering", label: "Assigned course offering", type: "select", optionKey: "offerings", required: true }, { name: "title", label: "Session title" }, { name: "starts_at", label: "Starts at", type: "datetime-local", required: true }, { name: "ends_at", label: "Ends at", type: "datetime-local", required: true }, { name: "notes", label: "Lecturer notes", type: "textarea" }],
        },
        "attendance-monitor": {
            resource, title: "Attendance monitoring", description: "Review attendance session activity across the institution. Verified attendance records are only created after both identity checks succeed.",
            columns: [{ key: "course_code", label: "Course" }, { key: "title", label: "Session" }, { key: "programme_name", label: "Programme" }, { key: "academic_session", label: "Academic session" }, { key: "starts_at", label: "Starts" }, { key: "status", label: "Status" }, { key: "registered_count", label: "Enrolled" }, { key: "attendance_count", label: "Present" }],
            readOnly: true,
        },
        "attendance-history": {
            resource, title: "Attendance history", description: "Review attendance entries recorded after successful QR Code and facial verification.",
            columns: [{ key: "course_code", label: "Course" }, { key: "course_title", label: "Course title" }, { key: "session_title", label: "Session" }, { key: "academic_session", label: "Academic session" }, { key: "recorded_at", label: "Recorded at" }],
            readOnly: true,
        },
    };
    return configs[resource] ?? {
        resource, title: "Workspace", description: "Manage your RollNexa information.", columns: [], readOnly: true,
    };
}

function formatCell(value: unknown, key: string): string {
    if (typeof value === "boolean") {
        if (key === "is_active") return value ? "Active" : "Inactive";
        if (key === "is_current") return value ? "Current" : "—";
        if (key === "registration_open") return value ? "Open" : "Closed";
        if (key === "is_registered") return value ? "Registered" : "Not registered";
        if (key === "is_cross_department") return value ? "Yes" : "No";
        return value ? "Yes" : "No";
    }
    if (value === null || value === undefined || value === "") return "—";
    if (key.endsWith("_at") && typeof value === "string") {
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }
    return String(value);
}

function getOptions(field: FieldSpec, options: Record<string, Choice[]> | undefined): Choice[] {
    if (field.options) return field.options;
    if (field.optionKey && options?.[field.optionKey]) return options[field.optionKey];
    return [];
}

function ResourceForm({
    config,
    item,
    options,
    onClose,
    onSubmit,
    isSaving,
    error,
}: {
    config: ResourceConfig;
    item: Row | null;
    options?: Record<string, Choice[]>;
    onClose: () => void;
    onSubmit: (values: Row) => void;
    isSaving: boolean;
    error: string;
}) {
    const [values, setValues] = useState<Row>({});

    useEffect(() => {
        const initial: Row = {};
        (config.fields ?? []).forEach((field) => {
            const relatedIdFields: Record<string, string> = {
                department: "department_id",
                programme: "programme_id",
                faculty: "faculty_id",
                session: "session_id",
                course: "course_id",
                semester: "semester_id",
                offering: "offering_id",
                lecturer: "lecturer_profile_id",
            };
            const sourceKey = item && item[field.name] !== undefined
                ? field.name
                : relatedIdFields[field.name];
            if (item && sourceKey && item[sourceKey] !== undefined) {
                initial[field.name] = item[sourceKey];
            } else if (field.type === "checkbox") {
                initial[field.name] = false;
            } else {
                initial[field.name] = "";
            }
        });
        if (config.resource === "users" && !item) initial.role = "student";
        if (config.resource === "offerings" && !item) initial.credit_units = 2;
        if (config.resource === "courses" && !item) initial.credit_units = 2;
        setValues(initial);
    }, [config, item]);

    function updateValue(name: string, value: unknown) {
        setValues((current) => ({ ...current, [name]: value }));
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        onSubmit(values);
    }

    const fields = (config.fields ?? []).filter((field) => {
        if (item && field.createOnly) return false;
        if (!item && field.editOnly) return false;
        return !field.visibleWhen || field.visibleWhen(values);
    });

    return (
        <div className="workspace-modal-backdrop" role="presentation" onMouseDown={(event) => {
            if (event.target === event.currentTarget) onClose();
        }}>
            <section className="workspace-modal" role="dialog" aria-modal="true" aria-labelledby="workspace-modal-title">
                <div className="workspace-modal-header">
                    <div>
                        <span className="eyebrow">{item ? "UPDATE RECORD" : "NEW RECORD"}</span>
                        <h2 id="workspace-modal-title">{item ? `Edit ${config.title.toLowerCase().replace(/s$/, "")}` : config.createLabel ?? `Add ${config.title.toLowerCase()}`}</h2>
                    </div>
                    <button className="workspace-icon-button" type="button" onClick={onClose} aria-label="Close form"><X size={19} /></button>
                </div>
                <form onSubmit={handleSubmit} className="workspace-form">
                    {error && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{error}</div>}
                    <div className="workspace-form-grid">
                        {fields.map((field) => {
                            const value = values[field.name] ?? "";
                            const inputId = `field-${field.name}`;
                            const choices = getOptions(field, options);
                            return (
                                <label className={`workspace-field ${field.type === "textarea" ? "workspace-field-wide" : ""} ${field.type === "checkbox" ? "workspace-checkbox-field" : ""}`} key={field.name} htmlFor={inputId}>
                                    {field.type === "checkbox" ? (
                                        <>
                                            <input id={inputId} type="checkbox" checked={Boolean(value)} onChange={(event) => updateValue(field.name, event.target.checked)} />
                                            <span>{field.label}</span>
                                        </>
                                    ) : (
                                        <>
                                            <span>{field.label}{field.required ? " *" : ""}</span>
                                            {field.type === "textarea" ? (
                                                <textarea id={inputId} rows={3} value={String(value)} required={field.required} onChange={(event) => updateValue(field.name, event.target.value)} />
                                            ) : field.type === "select" ? (
                                                <select id={inputId} value={String(value)} required={field.required} onChange={(event) => updateValue(field.name, event.target.value)}>
                                                    <option value="">Select {field.label.toLowerCase()}</option>
                                                    {choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
                                                </select>
                                            ) : (
                                                <input id={inputId} type={field.type ?? "text"} value={String(value)} required={field.required} min={field.type === "number" ? 1 : undefined} onChange={(event) => updateValue(field.name, field.type === "number" ? event.target.value : event.target.value)} />
                                            )}
                                            {field.help && <small>{field.help}</small>}
                                        </>
                                    )}
                                </label>
                            );
                        })}
                    </div>
                    <div className="workspace-modal-actions">
                        <button type="button" className="button button-outline" onClick={onClose}>Cancel</button>
                        <button type="submit" className="button button-primary" disabled={isSaving}>
                            {isSaving ? <LoaderCircle size={16} className="workspace-spin" /> : <Check size={16} />}
                            {isSaving ? "Saving…" : item ? "Save changes" : "Create record"}
                        </button>
                    </div>
                </form>
            </section>
        </div>
    );
}

function useWorkspaceData(resource: string, search: string, status: string, page: number, offeringId?: number, roleFilter = "") {
    const params = new URLSearchParams({ q: search, status, page: String(page), page_size: "20" });
    if (offeringId) params.set("offering", String(offeringId));
    if (roleFilter) params.set("role", roleFilter);
    return useQuery({
        queryKey: ["workspace", resource, search, status, page, offeringId, roleFilter],
        queryFn: () => apiRequest<WorkspaceResponse>(`/api/v1/workspace/${resource}/?${params.toString()}`),
    });
}

function ResourceWorkspace({
    config,
    search,
    statusFilter,
    page,
    setPage,
    roleFilter,
    onOfferingChange,
}: {
    config: ResourceConfig;
    search: string;
    statusFilter: string;
    page: number;
    setPage: (page: number) => void;
    roleFilter?: string;
    onOfferingChange?: (id: number) => void;
}) {
    const queryClient = useQueryClient();
    const dataQuery = useWorkspaceData(config.resource, search, statusFilter, page, undefined, roleFilter);
    const [editing, setEditing] = useState<Row | null>(null);
    const [creating, setCreating] = useState(false);
    const [mutationError, setMutationError] = useState("");
    const [temporaryPassword, setTemporaryPassword] = useState("");
    const [actionBusy, setActionBusy] = useState<number | null>(null);
    const mutation = useMutation({
        mutationFn: async (payload: { values: Row; item: Row | null }) => {
            const url = payload.item
                ? `/api/v1/workspace/${config.resource}/${payload.item.id}/`
                : `/api/v1/workspace/${config.resource}/`;
            return apiRequest<{ item: Row; temporary_password?: string }>(url, {
                method: payload.item ? "PATCH" : "POST",
                body: JSON.stringify(payload.values),
            });
        },
        onSuccess: (response) => {
            setCreating(false);
            setEditing(null);
            setMutationError("");
            if (response.temporary_password) setTemporaryPassword(response.temporary_password);
            void queryClient.invalidateQueries({ queryKey: ["workspace"] });
            void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        },
        onError: (error) => setMutationError(error instanceof Error ? error.message : "The record could not be saved."),
    });

    async function runAction(item: Row, action: string, body: Row = {}) {
        setActionBusy(Number(item.id));
        setMutationError("");
        try {
            await apiRequest(`/api/v1/workspace/${config.resource}/${item.id}/${action}/`, {
                method: "POST",
                body: JSON.stringify(body),
            });
            await queryClient.invalidateQueries({ queryKey: ["workspace"] });
            await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        } catch (error) {
            setMutationError(error instanceof Error ? error.message : "The action could not be completed.");
        } finally {
            setActionBusy(null);
        }
    }

    const results = dataQuery.data?.results ?? [];
    const options = dataQuery.data?.options;
    const canCreate = Boolean(config.fields && !config.readOnly);

    function rowActions(item: Row) {
        const actions: Array<{ label: string; action: string; tone?: string }> = [];
        if (config.resource === "users" || ["faculties", "departments", "programmes", "sessions", "semesters", "courses", "offerings"].includes(config.resource)) {
            if (config.fields) actions.push({ label: "Edit", action: "edit" });
            actions.push({ label: item.is_active ? "Deactivate" : "Activate", action: "toggle" });
        }
        if ((config.resource === "sessions" || config.resource === "semesters") && !item.is_current) {
            actions.push({ label: "Set current", action: "set-current" });
        }
        if (config.resource === "assignments" && item.is_active) actions.push({ label: "Revoke", action: "revoke" });
        if (config.resource === "student-courses" && item.registration_open) {
            actions.push({ label: item.is_registered ? "Withdraw" : "Register", action: item.is_registered ? "withdraw" : "register" });
        }
        if (config.resource === "attendance-sessions") {
            if (item.status === "scheduled") {
                if (item.can_activate) actions.push({ label: "Activate", action: "activate" });
                actions.push({ label: "Cancel", action: "cancel" });
            }
            if (item.status === "active") actions.push({ label: "Close", action: "close" });
        }
        if (config.resource === "lecturer-courses") actions.push({ label: "View roster", action: "roster" });
        return actions;
    }

    async function handleAction(item: Row, action: string) {
        if (action === "edit") {
            setMutationError("");
            setEditing(item);
            return;
        }
        if (action === "roster") {
            onOfferingChange?.(Number(item.id));
            return;
        }
        const labels: Record<string, string> = {
            toggle: "change this record's active status",
            "set-current": "make this the current academic period",
            revoke: "revoke this teaching assignment",
            register: "register for this course",
            withdraw: "withdraw from this course",
            activate: "activate this attendance session",
            close: "close this attendance session",
            cancel: "cancel this attendance session",
        };
        if (!window.confirm(`Are you sure you want to ${labels[action] ?? action}?`)) return;
        await runAction(item, action);
    }

    return (
        <>
            {mutationError && !creating && !editing && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{mutationError}</div>}
            {temporaryPassword && (
                <div className="workspace-alert workspace-alert-success workspace-credential-alert">
                    <ShieldCheck size={18} />
                    <div><strong>Account created. Copy the temporary password now.</strong><code>{temporaryPassword}</code><small>This credential is shown only in this response. The new user must change it at first sign-in.</small></div>
                    <button type="button" onClick={() => void navigator.clipboard?.writeText(temporaryPassword)}>Copy</button>
                    <button type="button" className="workspace-icon-button" onClick={() => setTemporaryPassword("")} aria-label="Dismiss"><X size={16} /></button>
                </div>
            )}
            {config.resource === "student-courses" && dataQuery.data && !dataQuery.data.profileComplete && (
                <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />Your student profile needs a programme and current level before course registration can be managed. Contact your administrator to update your academic assignment.</div>
            )}
            <div className="workspace-table-card">
                <div className="workspace-table-heading">
                    <div><strong>{dataQuery.data?.count ?? 0} records</strong><span>Showing {results.length} on this page</span></div>
                    {canCreate && <button className="button button-primary" type="button" onClick={() => { setMutationError(""); setCreating(true); }}><Plus size={16} />{config.createLabel ?? "Add record"}</button>}
                </div>
                {dataQuery.isLoading ? (
                    <div className="workspace-loading"><LoaderCircle size={22} className="workspace-spin" /> Loading records…</div>
                ) : dataQuery.isError ? (
                    <div className="workspace-empty"><AlertCircle size={24} /><strong>Unable to load this workspace</strong><p>{dataQuery.error instanceof Error ? dataQuery.error.message : "Please try again."}</p><button className="button button-outline" onClick={() => void dataQuery.refetch()}><RefreshCw size={15} /> Retry</button></div>
                ) : results.length === 0 ? (
                    <div className="workspace-empty"><ClipboardList size={25} /><strong>No records found</strong><p>{config.emptyText ?? "There are no records matching the current filters."}</p></div>
                ) : (
                    <div className="workspace-table-scroll">
                        <table className="workspace-data-table">
                            <thead><tr>{config.columns.map((column) => <th key={column.key}>{column.label}</th>)}<th className="workspace-actions-heading">Actions</th></tr></thead>
                            <tbody>
                                {results.map((item) => {
                                    const actions = rowActions(item);
                                    return (
                                        <tr key={String(item.id)}>
                                            {config.columns.map((column) => (
                                                <td key={column.key}>
                                                    {column.key === "is_active" || column.key === "status" || column.key === "registration_open" || column.key === "is_registered" ? (
                                                        <span className={`workspace-status ${String(item[column.key]) === "true" || item[column.key] === "active" || item[column.key] === true ? "is-positive" : "is-neutral"}`}>{formatCell(item[column.key], column.key)}</span>
                                                    ) : <span>{formatCell(item[column.key], column.key)}</span>}
                                                </td>
                                            ))}
                                            <td><div className="workspace-row-actions">
                                                {actions.map((entry) => (
                                                    <button key={entry.action} type="button" className={`workspace-action-button ${entry.action === "toggle" || entry.action === "revoke" || entry.action === "cancel" ? "is-muted" : ""}`} disabled={actionBusy === Number(item.id)} onClick={() => void handleAction(item, entry.action)}>
                                                        {actionBusy === Number(item.id) ? <LoaderCircle size={13} className="workspace-spin" /> : entry.action === "edit" ? <Edit3 size={13} /> : null}{entry.label}
                                                    </button>
                                                ))}
                                                {!actions.length && <span className="workspace-no-action">—</span>}
                                            </div></td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
                {dataQuery.data && dataQuery.data.pages > 1 && (
                    <div className="workspace-pagination">
                        <span>Page {dataQuery.data.page} of {dataQuery.data.pages}</span>
                        <div>
                            <button type="button" className="workspace-icon-button" disabled={!dataQuery.data.hasPrevious} onClick={() => setPage(Math.max(1, page - 1))} aria-label="Previous page"><ChevronLeft size={17} /></button>
                            <button type="button" className="workspace-icon-button" disabled={!dataQuery.data.hasNext} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight size={17} /></button>
                        </div>
                    </div>
                )}
            </div>
            {(creating || editing) && (
                <ResourceForm
                    config={config}
                    item={editing}
                    options={options}
                    onClose={() => { setCreating(false); setEditing(null); setMutationError(""); }}
                    onSubmit={(values) => mutation.mutate({ values, item: editing })}
                    isSaving={mutation.isPending}
                    error={mutationError}
                />
            )}
        </>
    );
}

function RosterWorkspace() {
    const coursesQuery = useWorkspaceData("lecturer-courses", "", "", 1);
    const [searchParams, setSearchParams] = useSearchParams();
    const initialOffering = Number(searchParams.get("offering")) || undefined;
    const [offeringId, setOfferingId] = useState<number | undefined>(initialOffering);
    const [page, setPage] = useState(1);
    const rosterQuery = useQuery({
        queryKey: ["workspace", "rosters", offeringId, page],
        queryFn: () => apiRequest<WorkspaceResponse>(`/api/v1/workspace/rosters/?offering=${offeringId}&page=${page}&page_size=100`),
        enabled: Boolean(offeringId),
    });

    const courses = coursesQuery.data?.results ?? [];
    useEffect(() => {
        if (!offeringId && courses.length) setOfferingId(Number(courses[0].id));
    }, [courses, offeringId]);
    useEffect(() => {
        if (offeringId) setSearchParams({ offering: String(offeringId) }, { replace: true });
    }, [offeringId, setSearchParams]);

    return (
        <>
            <div className="workspace-filter-row workspace-roster-picker">
                <label>Course offering
                    <select value={offeringId ?? ""} onChange={(event) => { setOfferingId(Number(event.target.value) || undefined); setPage(1); }}>
                        <option value="">Select an assigned course</option>
                        {courses.map((course) => <option key={String(course.id)} value={String(course.id)}>{String(course.course_code)} — {String(course.course_title)} · {String(course.programme_name)}</option>)}
                    </select>
                </label>
            </div>
            <div className="workspace-table-card">
                <div className="workspace-table-heading"><div><strong>Registered students</strong><span>{rosterQuery.data?.count ?? 0} current registrations</span></div></div>
                {!offeringId ? <div className="workspace-empty"><BookOpen size={24} /><strong>No assigned courses available</strong><p>Your active course offerings will appear here.</p></div> : rosterQuery.isLoading ? <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading class roster…</div> : rosterQuery.isError ? <div className="workspace-empty"><AlertCircle size={22} /><p>Unable to load this class roster.</p></div> : (rosterQuery.data?.results ?? []).length === 0 ? <div className="workspace-empty"><UserRound size={24} /><strong>No registered students</strong><p>Students who register for this course offering will appear here.</p></div> : (
                    <>
                        <div className="workspace-table-scroll"><table className="workspace-data-table"><thead><tr><th>Student</th><th>Username</th><th>Institutional ID</th><th>Email</th><th>Programme</th><th>Level</th><th>Registered</th></tr></thead><tbody>{rosterQuery.data?.results.map((student) => <tr key={String(student.id)}><td><strong>{String(student.name)}</strong></td><td>{String(student.username)}</td><td>{String(student.institutional_id || "—")}</td><td>{String(student.email || "—")}</td><td>{String(student.programme || "—")}</td><td>{String(student.level || "—")}</td><td>{formatCell(student.registered_at, "registered_at")}</td></tr>)}</tbody></table></div>
                        {rosterQuery.data && rosterQuery.data.pages > 1 && <div className="workspace-pagination"><span>Page {rosterQuery.data.page} of {rosterQuery.data.pages}</span><div><button type="button" className="workspace-icon-button" disabled={!rosterQuery.data.hasPrevious} onClick={() => setPage((current) => Math.max(1, current - 1))} aria-label="Previous page"><ChevronLeft size={17} /></button><button type="button" className="workspace-icon-button" disabled={!rosterQuery.data.hasNext} onClick={() => setPage((current) => current + 1)} aria-label="Next page"><ChevronRight size={17} /></button></div></div>}
                    </>
                )}
            </div>
        </>
    );
}

function ReportsWorkspace() {
    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ["workspace", "reports"],
        queryFn: () => apiRequest<ReportsResponse>("/api/v1/workspace/reports/"),
    });
    const role = data?.role ?? "";
    const metrics = [
        { label: "Attendance sessions", value: data?.attendance.sessions ?? 0 },
        { label: "Verified attendance records", value: data?.attendance.verifiedRecords ?? 0 },
        { label: "Scheduled sessions", value: data?.attendance.scheduled ?? 0 },
        { label: "Closed sessions", value: data?.attendance.closed ?? 0 },
    ];
    return (
        <>
            {isLoading ? <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading reports…</div> : isError ? <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />Unable to load reporting data. <button onClick={() => void refetch()}>Retry</button></div> : (
                <>
                    <div className="workspace-metric-grid">{metrics.map((metric) => <article className="workspace-metric-card" key={metric.label}><span>{metric.label}</span><strong>{metric.value.toLocaleString()}</strong></article>)}</div>
                    {data?.academic && <section className="workspace-table-card workspace-report-card"><div className="workspace-table-heading"><div><strong>Academic overview</strong><span>Current platform records</span></div></div><div className="workspace-report-stats">{Object.entries(data.academic).map(([key, value]) => <div key={key}><strong>{value.toLocaleString()}</strong><span>{key.replace(/([A-Z])/g, " $1").replace(/^./, (letter) => letter.toUpperCase())}</span></div>)}</div></section>}
                    {data?.notice && <div className="workspace-alert workspace-alert-warning"><AlertCircle size={17} />{data.notice}</div>}
                    <div className="workspace-table-card"><div className="workspace-table-heading"><div><strong>Recent attendance sessions</strong><span>Latest sessions in your authorised scope</span></div></div>{data?.recentSessions.length ? <div className="workspace-table-scroll"><table className="workspace-data-table"><thead><tr><th>Course</th><th>Session</th><th>Academic session</th><th>Starts</th><th>Status</th><th>Enrolled</th><th>Present</th></tr></thead><tbody>{data.recentSessions.map((item) => <tr key={String(item.id)}><td><strong>{String(item.course_code)}</strong><small className="workspace-cell-subtitle">{String(item.course_title)}</small></td><td>{String(item.title || "Attendance session")}</td><td>{String(item.academic_session)}</td><td>{formatCell(item.starts_at, "starts_at")}</td><td><span className="workspace-status">{String(item.status)}</span></td><td>{String(item.registered_count)}</td><td>{String(item.attendance_count)}</td></tr>)}</tbody></table></div> : <div className="workspace-empty"><ClipboardList size={24} /><strong>No attendance sessions yet</strong><p>Session activity will appear here as lecturers schedule classes.</p></div>}</div>
                </>
            )}
            <p className="workspace-report-footnote">{role === "admin" ? "Administrative report figures are derived from the current academic and attendance records." : "Report data is restricted to your active teaching assignments."}</p>
        </>
    );
}

function ProfileWorkspace() {
    const queryClient = useQueryClient();
    const profileQuery = useQuery({
        queryKey: ["workspace", "profile"],
        queryFn: () => apiRequest<{ item: Row }>("/api/v1/workspace/profile/"),
    });
    const [values, setValues] = useState<Row>({});
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");
    const mutation = useMutation({
        mutationFn: () => apiRequest<{ item: Row }>("/api/v1/workspace/profile/", {
            method: "PATCH",
            body: JSON.stringify(values),
        }),
        onSuccess: async (response) => {
            setMessage("Your profile has been updated.");
            setError("");
            queryClient.setQueryData(["workspace", "profile"], response);
            await queryClient.invalidateQueries({ queryKey: ["auth", "session"] });
        },
        onError: (requestError) => setError(requestError instanceof Error ? requestError.message : "Your profile could not be updated."),
    });
    useEffect(() => {
        if (profileQuery.data?.item) {
            const item = profileQuery.data.item;
            setValues({ first_name: item.first_name, last_name: item.last_name, email: item.email, phone_number: item.phone_number });
        }
    }, [profileQuery.data]);

    return (
        <div className="workspace-profile-card">
            <div className="workspace-profile-heading"><span className="workspace-profile-avatar"><UserRound size={25} /></span><div><h2>Personal information</h2><p>Update the contact details associated with your RollNexa account.</p></div></div>
            {profileQuery.isLoading ? <div className="workspace-loading"><LoaderCircle className="workspace-spin" /> Loading profile…</div> : (
                <form className="workspace-form" onSubmit={(event) => { event.preventDefault(); setMessage(""); mutation.mutate(); }}>
                    {error && <div className="workspace-alert workspace-alert-error"><AlertCircle size={17} />{error}</div>}
                    {message && <div className="workspace-alert workspace-alert-success"><Check size={17} />{message}</div>}
                    <div className="workspace-form-grid">
                        {(["first_name", "last_name", "email", "phone_number"] as const).map((field) => <label className="workspace-field" key={field}><span>{({ first_name: "First name", last_name: "Last name", email: "Email address", phone_number: "Phone number" })[field]}</span><input type={field === "email" ? "email" : "text"} value={String(values[field] ?? "")} required={field !== "phone_number"} onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.value }))} /></label>)}
                    </div>
                    <div className="workspace-profile-readonly"><div><span>Username</span><strong>{String(profileQuery.data?.item.username ?? "—")}</strong></div><div><span>Role</span><strong>{String(profileQuery.data?.item.role ?? "—")}</strong></div><div><span>Institutional ID</span><strong>{String(profileQuery.data?.item.institutional_id || "Not assigned")}</strong></div></div>
                    <div className="workspace-modal-actions"><Link className="button button-outline" to="/app/password-change">Change password</Link><button className="button button-primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Saving…" : "Save profile"}<ArrowRight size={15} /></button></div>
                </form>
            )}
        </div>
    );
}

export function WorkspacePage() {
    const { user } = useAuth();
    const location = useLocation();
    const section = location.pathname.split("/")[2] ?? "overview";
    const role = user?.role ?? "student";
    const [academicResource, setAcademicResource] = useState("faculties");
    const [courseResource, setCourseResource] = useState("courses");
    const [search, setSearch] = useState("");
    const [searchValue, setSearchValue] = useState("");
    const [statusFilter, setStatusFilter] = useState("");
    const [roleFilter, setRoleFilter] = useState("");
    const [page, setPage] = useState(1);

    useEffect(() => {
        setSearch("");
        setSearchValue("");
        setStatusFilter("");
        setRoleFilter("");
        setPage(1);
    }, [section]);

    let resource = "";
    if (section === "users") resource = "users";
    if (section === "academic") resource = academicResource;
    if (section === "courses") {
        resource = role === "admin" ? courseResource : role === "lecturer" ? "lecturer-courses" : "student-courses";
    }
    if (section === "rosters") resource = "rosters";
    if (section === "attendance") resource = role === "admin" ? "attendance-monitor" : role === "lecturer" ? "attendance-sessions" : "student-courses";
    if (section === "history") resource = "attendance-history";

    const config = useMemo(() => getResourceConfig(resource, role), [resource, role]);
    const navigate = useNavigate();
    const showTabs = section === "academic" || (section === "courses" && role === "admin");
    const pageTitle = section === "attendance" && role === "student" ? "Attendance check-in" : config.title;
    const pageDescription = section === "attendance" && role === "student"
        ? "Student attendance check-in will become available when secure QR Code and facial verification are implemented together."
        : config.description;

    if (section === "reports") {
        return <div className="dashboard-page workspace-page"><PageHeading title="Reports and analytics" description="Review academic activity and attendance-session summaries available to your role." /><ReportsWorkspace /></div>;
    }
    if (section === "profile" || section === "settings") {
        return <div className="dashboard-page workspace-page"><PageHeading title={section === "profile" ? "My profile" : "Account settings"} description="Manage your personal details and account security." /><ProfileWorkspace /></div>;
    }
    if (section === "rosters") {
        return <div className="dashboard-page workspace-page"><PageHeading title="Class rosters" description="Select an assigned course offering to view its currently registered students." /><RosterWorkspace /></div>;
    }
    if (section === "attendance" && role === "student") {
        return <div className="dashboard-page workspace-page"><PageHeading title={pageTitle} description={pageDescription} /><div className="workspace-feature-notice"><span><ShieldCheck size={26} /></span><h2>Dual verification is required</h2><p>RollNexa will only record attendance after a valid session QR Code has been scanned and the student's face has been successfully verified. Neither check-in method will be available independently.</p><span className="workspace-coming-soon">QR and facial verification are scheduled for subsequent releases.</span></div></div>;
    }

    return (
        <div className="dashboard-page workspace-page">
            <PageHeading title={pageTitle} description={pageDescription} />
            {showTabs && (
                <div className="workspace-tabs" role="tablist" aria-label="Workspace categories">
                    {(section === "academic" ? academicTabs : courseTabs).map((tab) => {
                        const active = section === "academic" ? academicResource === tab.resource : courseResource === tab.resource;
                        return <button type="button" role="tab" aria-selected={active} className={active ? "is-active" : ""} key={tab.resource} onClick={() => { if (section === "academic") setAcademicResource(tab.resource); else setCourseResource(tab.resource); setPage(1); setStatusFilter(""); setRoleFilter(""); setSearch(""); setSearchValue(""); }}>{tab.label}</button>;
                    })}
                </div>
            )}
            <div className="workspace-filter-row">
                <label className="workspace-search"><Search size={17} /><input value={searchValue} onChange={(event) => setSearchValue(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { setSearch(searchValue); setPage(1); } }} placeholder={`Search ${config.title.toLowerCase()}…`} /><button type="button" onClick={() => { setSearch(searchValue); setPage(1); }}>Search</button></label>
                {resource === "users" && <label className="workspace-filter-select"><UserRound size={15} /><select value={roleFilter} onChange={(event) => { setRoleFilter(event.target.value); setPage(1); }}><option value="">All account roles</option><option value="student">Students</option><option value="lecturer">Lecturers</option></select></label>}
                {(["users", "faculties", "departments", "programmes", "sessions", "semesters", "courses", "offerings", "assignments", "attendance-sessions", "attendance-monitor"].includes(resource)) && (
                    <label className="workspace-filter-select"><Filter size={15} /><select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}>
                        <option value="">All statuses</option>
                        {resource === "attendance-sessions" || resource === "attendance-monitor" ? <><option value="scheduled">Scheduled</option><option value="active">Active</option><option value="closed">Closed</option><option value="cancelled">Cancelled</option></> : resource === "assignments" ? <><option value="active">Active</option><option value="history">History</option><option value="all">All</option></> : <><option value="active">Active</option><option value="inactive">Inactive</option>{resource === "offerings" && <><option value="open">Registration open</option><option value="closed">Registration closed</option></>}</>}
                    </select></label>
                )}
            </div>
            <ResourceWorkspace
                key={resource}
                config={config}
                search={search}
                statusFilter={statusFilter}
                page={page}
                setPage={setPage}
                roleFilter={roleFilter}
                onOfferingChange={(id) => navigate(`/app/rosters?offering=${id}`)}
            />
            {section === "attendance" && role === "admin" && <p className="workspace-report-footnote">Administrative monitoring is read-only. Attendance records cannot be manually added or edited.</p>}
        </div>
    );
}

function PageHeading({ title, description }: { title: string; description: string }) {
    return <div className="dashboard-page-heading workspace-page-heading"><div><span className="eyebrow">ROLLNEXA WORKSPACE</span><h1>{title}</h1><p>{description}</p></div><span className="release-chip"><span /> ROLLNEXA 0.8.0</span></div>;
}
