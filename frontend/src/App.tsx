import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { DashboardHome, PasswordChangePage, ProtectedRoute } from "./pages/DashboardPages";
import { WorkspacePage } from "./pages/WorkspacePage";
import { AttendanceQRPage, AttendanceScanPage } from "./pages/AttendanceQRPages";
import { LoginPage } from "./pages/LoginPage";
import {
    AboutPage,
    ContactPage,
    FeaturesPage,
    HomePage,
    HowItWorksPage,
    PrivacyPage,
    TermsPage,
} from "./pages/PublicPages";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

function NotFoundPage() {
    return (
        <div className="not-found-page">
            <span className="eyebrow">404 · PAGE NOT FOUND</span>
            <h1>This page is not available.</h1>
            <p>The page may have moved or may not be part of this RollNexa release.</p>
            <a className="button button-primary" href="/">Return home</a>
        </div>
    );
}

export default function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <AuthProvider>
                    <Routes>
                        <Route element={<PublicLayout />}>
                            <Route path="/" element={<HomePage />} />
                            <Route path="/about" element={<AboutPage />} />
                            <Route path="/features" element={<FeaturesPage />} />
                            <Route path="/how-it-works" element={<HowItWorksPage />} />
                            <Route path="/contact" element={<ContactPage />} />
                            <Route path="/privacy" element={<PrivacyPage />} />
                            <Route path="/terms" element={<TermsPage />} />
                        </Route>
                        <Route path="/login" element={<LoginPage />} />
                        <Route
                            path="/app"
                            element={(
                                <ProtectedRoute>
                                    <DashboardLayout />
                                </ProtectedRoute>
                            )}
                        >
                            <Route index element={<DashboardHome />} />
                            <Route path="password-change" element={<PasswordChangePage />} />
                            <Route path="users" element={<WorkspacePage />} />
                            <Route path="academic" element={<WorkspacePage />} />
                            <Route path="courses" element={<WorkspacePage />} />
                            <Route path="rosters" element={<WorkspacePage />} />
                            <Route path="attendance" element={<WorkspacePage />} />
                            <Route path="attendance/check-in" element={<AttendanceScanPage />} />
                            <Route path="attendance/sessions/:sessionId/qr" element={<AttendanceQRPage />} />
                            <Route path="history" element={<WorkspacePage />} />
                            <Route path="reports" element={<WorkspacePage />} />
                            <Route path="settings" element={<WorkspacePage />} />
                            <Route path="profile" element={<WorkspacePage />} />
                            <Route path="*" element={<Navigate to="/app" replace />} />
                        </Route>
                        <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                </AuthProvider>
            </BrowserRouter>
        </QueryClientProvider>
    );
}
