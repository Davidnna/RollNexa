import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "../lib/api";

export interface RollNexaUser {
    id: number;
    username: string;
    firstName: string;
    lastName: string;
    fullName: string;
    email: string;
    role: "admin" | "lecturer" | "student" | null;
    institutionalId: string;
    phoneNumber: string;
    department: string | null;
    programme: string | null;
    currentLevel: string;
    mustChangePassword: boolean;
    isActive: boolean;
}

interface SessionResponse {
    authenticated: boolean;
    user: RollNexaUser | null;
}

interface LoginResponse extends SessionResponse {
    redirectTo: string;
}

interface AuthContextValue {
    user: RollNexaUser | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<RollNexaUser>;
    logout: () => Promise<void>;
    refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const queryClient = useQueryClient();
    const sessionQuery = useQuery({
        queryKey: ["auth", "session"],
        queryFn: () => apiRequest<SessionResponse>("/api/v1/auth/session/"),
        retry: false,
        staleTime: 30_000,
        refetchOnWindowFocus: true,
    });

    const loginMutation = useMutation({
        mutationFn: (credentials: { username: string; password: string }) =>
            apiRequest<LoginResponse>("/api/v1/auth/login/", {
                method: "POST",
                body: JSON.stringify(credentials),
            }),
        onSuccess: (data) => {
            queryClient.setQueryData(["auth", "session"], data);
        },
    });

    const logoutMutation = useMutation({
        mutationFn: () => apiRequest<{ authenticated: false }>("/api/v1/auth/logout/", {
            method: "POST",
            body: JSON.stringify({}),
        }),
        onSuccess: () => {
            queryClient.setQueryData(["auth", "session"], {
                authenticated: false,
                user: null,
            });
            queryClient.removeQueries({ queryKey: ["dashboard"] });
        },
    });

    const value = useMemo<AuthContextValue>(() => ({
        user: sessionQuery.data?.user ?? null,
        isAuthenticated: Boolean(sessionQuery.data?.authenticated && sessionQuery.data.user),
        isLoading: sessionQuery.isLoading,
        login: async (username, password) => {
            const response = await loginMutation.mutateAsync({ username, password });
            if (!response.user) {
                throw new Error("The server did not return an authenticated user.");
            }
            return response.user;
        },
        logout: async () => {
            await logoutMutation.mutateAsync();
        },
        refreshSession: async () => {
            await sessionQuery.refetch();
        },
    }), [sessionQuery.data, sessionQuery.isLoading, loginMutation, logoutMutation, sessionQuery]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider.");
    }
    return context;
}
