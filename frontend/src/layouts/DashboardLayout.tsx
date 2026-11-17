import { useState } from "react";
import {
    Activity,
    BookOpen,
    Building2,
    CalendarDays,
    ChevronDown,
    ClipboardCheck,
    FileBarChart,
    GraduationCap,
    LayoutDashboard,
    LogOut,
    Menu,
    Settings,
    Users,
    QrCode,
    X,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

interface NavigationItem {
    label: string;
    to: string;
    icon: typeof LayoutDashboard;
}

const navigation: Record<string, NavigationItem[]> = {
    admin: [
        { label: "Overview", to: "/app", icon: LayoutDashboard },
        { label: "User management", to: "/app/users", icon: Users },
        { label: "Academic structure", to: "/app/academic", icon: Building2 },
        { label: "Course management", to: "/app/courses", icon: BookOpen },
        { label: "Attendance", to: "/app/attendance", icon: ClipboardCheck },
        { label: "Reports", to: "/app/reports", icon: FileBarChart },
        { label: "Settings", to: "/app/settings", icon: Settings },
    ],
    lecturer: [
        { label: "Overview", to: "/app", icon: LayoutDashboard },
        { label: "My courses", to: "/app/courses", icon: BookOpen },
        { label: "Class rosters", to: "/app/rosters", icon: Users },
        { label: "Attendance sessions", to: "/app/attendance", icon: ClipboardCheck },
        { label: "Reports", to: "/app/reports", icon: FileBarChart },
        { label: "Profile", to: "/app/profile", icon: Settings },
    ],
    student: [
        { label: "Overview", to: "/app", icon: LayoutDashboard },
        { label: "My courses", to: "/app/courses", icon: BookOpen },
        { label: "Attendance", to: "/app/attendance", icon: ClipboardCheck },
        { label: "Scan QR Code", to: "/app/attendance/check-in", icon: QrCode },
        { label: "Attendance history", to: "/app/history", icon: CalendarDays },
        { label: "Profile", to: "/app/profile", icon: Settings },
    ],
};

const roleLabels: Record<string, string> = {
    admin: "System administrator",
    lecturer: "Lecturer workspace",
    student: "Student workspace",
};

export function DashboardLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [profileMenuOpen, setProfileMenuOpen] = useState(false);
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const items = navigation[user?.role ?? "student"] ?? navigation.student;

    async function handleLogout() {
        await logout();
        navigate("/", { replace: true });
    }

    return (
        <div className="dashboard-shell">
            {sidebarOpen && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setSidebarOpen(false)} />}
            <aside className={`dashboard-sidebar ${sidebarOpen ? "is-open" : ""}`}>
                <div className="sidebar-brand-row">
                    <NavLink to="/app" className="sidebar-brand" onClick={() => setSidebarOpen(false)}>
                        <img src="/static/images/rollnexa-logo.svg" alt="RollNexa" />
                    </NavLink>
                    <button className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
                        <X size={20} />
                    </button>
                </div>
                <div className="workspace-label">WORKSPACE</div>
                <div className="workspace-role">
                    <span className="workspace-role-icon"><GraduationCap size={17} /></span>
                    <span>{roleLabels[user?.role ?? "student"]}</span>
                </div>
                <nav className="dashboard-nav" aria-label="Dashboard navigation">
                    {items.map((item) => {
                        const Icon = item.icon;
                        return (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.to === "/app" || (item.to === "/app/attendance" && user?.role === "student")}
                                className={({ isActive }) => `dashboard-nav-link ${isActive ? "is-active" : ""}`}
                                onClick={() => setSidebarOpen(false)}
                            >
                                <Icon size={18} strokeWidth={1.8} />
                                <span>{item.label}</span>
                            </NavLink>
                        );
                    })}
                </nav>
                <div className="sidebar-bottom">
                    <div className="sidebar-help-card">
                        <span className="help-card-icon"><Activity size={17} /></span>
                        <strong>RollNexa 0.9.1</strong>
                        <p>Manage your academic workflows from one secure workspace.</p>
                    </div>
                    <button className="sidebar-logout" onClick={handleLogout}>
                        <LogOut size={17} />
                        <span>Sign out</span>
                    </button>
                </div>
            </aside>

            <div className="dashboard-main">
                <header className="dashboard-topbar">
                    <button className="topbar-menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
                        <Menu size={21} />
                    </button>
                    <div className="topbar-context">
                        <span className="topbar-eyebrow">ROLLNEXA WORKSPACE</span>
                        <span className="topbar-title">{roleLabels[user?.role ?? "student"]}</span>
                    </div>
                    <div className="topbar-actions">
                        <div className="profile-menu-wrap">
                            <button className="profile-trigger" onClick={() => setProfileMenuOpen((open) => !open)} aria-expanded={profileMenuOpen}>
                                <span className="avatar-circle">{user?.fullName?.slice(0, 1).toUpperCase() ?? "U"}</span>
                                <span className="profile-trigger-copy">
                                    <strong>{user?.fullName ?? "RollNexa user"}</strong>
                                    <small>{user?.role ?? "Account"}</small>
                                </span>
                                <ChevronDown size={16} />
                            </button>
                            {profileMenuOpen && (
                                <div className="profile-menu">
                                    <div className="profile-menu-identity">
                                        <strong>{user?.fullName}</strong>
                                        <span>{user?.email || user?.username}</span>
                                    </div>
                                    <NavLink to="/app/password-change" onClick={() => setProfileMenuOpen(false)}>Change password</NavLink>
                                    <button onClick={handleLogout}><LogOut size={15} /> Sign out</button>
                                </div>
                            )}
                        </div>
                    </div>
                </header>
                <main className="dashboard-content">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
