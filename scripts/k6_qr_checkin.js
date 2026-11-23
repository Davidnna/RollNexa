import http from "k6/http";
import { check, fail, sleep } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";

const baseUrl = (__ENV.BASE_URL || "").replace(/\/$/, "");
const qrToken = __ENV.QR_TOKEN || "";
const mode = (__ENV.MODE || "distinct").toLowerCase();
const students = new SharedArray("rollnexa-test-students", () => {
    const raw = __ENV.STUDENTS_JSON || "[]";
    return JSON.parse(raw);
});
const concurrency = Number(__ENV.CONCURRENCY || (mode === "same-student" ? 8 : students.length));

const qrCheckinDuration = new Trend("qr_checkin_duration", true);
const newPendingVerifications = new Counter("qr_new_pending_verifications");
const reusedPendingVerifications = new Counter("qr_reused_pending_verifications");

if (!baseUrl || !qrToken || students.length === 0) {
    throw new Error("Set BASE_URL, QR_TOKEN and STUDENTS_JSON before running this test.");
}
if (!["distinct", "same-student"].includes(mode)) {
    throw new Error("MODE must be either 'distinct' or 'same-student'.");
}
if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 8) {
    throw new Error("CONCURRENCY must be an integer between one and eight.");
}
if (mode === "same-student" && students.length !== 1) {
    throw new Error("same-student mode requires exactly one test student in STUDENTS_JSON.");
}
if (mode === "distinct" && students.length !== concurrency) {
    throw new Error("distinct mode requires exactly one unique test student per VU.");
}

export const options = {
    scenarios: {
        concurrent_qr_checkins: {
            executor: "per-vu-iterations",
            vus: concurrency,
            iterations: 1,
            maxDuration: "60s",
        },
    },
    thresholds: {
        checks: ["rate==1"],
        http_req_failed: ["rate==0"],
        qr_checkin_duration: ["p(95)<5000"],
        qr_new_pending_verifications: [
            `count==${mode === "same-student" ? 1 : concurrency}`,
        ],
        qr_reused_pending_verifications: [
            `count==${mode === "same-student" ? concurrency - 1 : 0}`,
        ],
    },
};

export default function () {
    const student = students[mode === "same-student" ? 0 : __VU - 1];
    if (!student || !student.username || !student.password) {
        fail("Each VU must have the required test-student username and password.");
    }

    const csrfResponse = http.get(`${baseUrl}/api/v1/csrf/`);
    const csrfToken = csrfResponse.status === 200 ? csrfResponse.json("csrfToken") : "";
    if (!check(csrfResponse, {
        "CSRF endpoint responds": (response) => response.status === 200,
        "CSRF token is returned": () => typeof csrfToken === "string" && csrfToken.length > 0,
    })) {
        fail("Could not initialise the CSRF session.");
    }

    const loginResponse = http.post(
        `${baseUrl}/api/v1/auth/login/`,
        JSON.stringify({ username: student.username, password: student.password }),
        {
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
        },
    );
    const authenticatedCsrfToken = loginResponse.status === 200
        ? loginResponse.json("csrfToken")
        : "";
    if (!check(loginResponse, {
        "student login succeeds": (response) => response.status === 200,
        "authenticated CSRF token is returned": () => (
            typeof authenticatedCsrfToken === "string" && authenticatedCsrfToken.length > 0
        ),
    })) {
        fail("A test student could not log in. Check account status and the configured login throttle.");
    }

    // Bring independently authenticated VUs close together before the race-sensitive request.
    sleep(0.25);
    const startedAt = Date.now();
    const verificationResponse = http.post(
        `${baseUrl}/api/v1/attendance/verify-qr/`,
        JSON.stringify({ token: qrToken }),
        {
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": authenticatedCsrfToken,
            },
        },
    );
    qrCheckinDuration.add(Date.now() - startedAt);

    const acceptedStatus = verificationResponse.status === 200 || verificationResponse.status === 201;
    const body = acceptedStatus ? verificationResponse.json() : {};
    const isNewPending = verificationResponse.status === 201 && body.alreadyVerified === false;
    const isReusedPending = verificationResponse.status === 200 && body.alreadyVerified === true;
    newPendingVerifications.add(isNewPending ? 1 : 0);
    reusedPendingVerifications.add(isReusedPending ? 1 : 0);

    check(verificationResponse, {
        "QR check-in is accepted": () => acceptedStatus,
        "verification remains pending facial confirmation": () => body.status === "qr_verified",
        "idempotent response state is consistent": () => isNewPending || isReusedPending,
        "verification identifier is returned": () => typeof body.verificationId === "string" && body.verificationId.length > 0,
    });
}
