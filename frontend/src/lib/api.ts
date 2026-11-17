export interface ApiError extends Error {
    status: number;
    data: Record<string, unknown>;
}

let csrfToken: string | null = null;

async function getCsrfToken(): Promise<string> {
    const response = await fetch("/api/v1/csrf/", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
    });

    if (!response.ok) {
        throw new Error("Unable to initialise the secure session. Refresh the page and try again.");
    }

    const data = (await response.json()) as { csrfToken: string };
    csrfToken = data.csrfToken;
    return csrfToken;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
    const method = (options.method ?? "GET").toUpperCase();
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");

    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
    if (options.body && !isFormData && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }

    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
        const token = csrfToken ?? (await getCsrfToken());
        headers.set("X-CSRFToken", token);
    }

    const response = await fetch(path, {
        ...options,
        method,
        headers,
        credentials: "same-origin",
    });

    const data = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (data && typeof data === "object" && "csrfToken" in data && typeof data.csrfToken === "string") {
        csrfToken = data.csrfToken;
    }
    if (!response.ok) {
        const payload = (data ?? {}) as Record<string, unknown>;
        const error = new Error(
            typeof payload.detail === "string" ? payload.detail : "The request could not be completed.",
        ) as ApiError;
        error.status = response.status;
        error.data = payload;
        throw error;
    }

    return data as T;
}
