import http from "k6/http";
import { check, fail, sleep } from "k6";
import { SharedArray } from "k6/data";
import { Trend } from "k6/metrics";

const baseUrl = (__ENV.BASE_URL || "").replace(/\/$/, "");
const qrToken = __ENV.QR_TOKEN || "";
const students = new SharedArray("rollnexa-test-students", () => {
    const raw = __ENV.STUDENTS_JSON || "[]";
    return JSON.parse(raw);
});
const qrCheckinDuration = new Trend("qr_checkin_duration", true);

if (!baseUrl || !qrToken || students.length === 0) {
    throw new Error("Set BASE_URL, QR_TOKEN and STUDENTS_JSON before running this test.");
}
if (students.length > 8) {
    throw new Error("Use no more than eight distinct students per run; the login and QR API throttles are intentionally conservative.");
}

export const options = {
    scenarios: {
        concurrent_qr_checkins: {
            executor: "per-vu-iterations",
            vus: students.length,
            iterations: 1,
            maxDuration: "60s",
        },
    },
    thresholds: {
        http_req_failed: ["rate<0.05"],
        qr_checkin_duration: ["p(95)<3000"],
    },
};

export default function () {
    const student = students[__VU - 1];
    if (!student || !student.username || !student.password) {
        fail("Each VU must have a distinct student username and password.");
    }

    const csrfResponse = http.get(`${baseUrl}/api/v1/csrf/`);
    if (!check(csrfResponse, { "CSRF endpoint responds": (response) => response.status === 200 })) {
        fail("Could not initialise the CSRF session.");
    }

    const loginResponse = http.post(
        `${baseUrl}/api/v1/auth/login/`,
        JSON.stringify({ username: student.username, password: student.password }),
        {
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfResponse.json("csrfToken"),
            },
        },
    );
    if (!check(loginResponse, { "student login succeeds": (response) => response.status === 200 })) {
        fail("A test student could not log in. Check account status and the configured login throttle.");
    }

    const startedAt = Date.now();
    const verificationResponse = http.post(
        `${baseUrl}/api/v1/attendance/verify-qr/`,
        JSON.stringify({ token: qrToken }),
        {
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": loginResponse.json("csrfToken"),
            },
        },
    );
    qrCheckinDuration.add(Date.now() - startedAt);

    check(verificationResponse, {
        "QR check-in is accepted": (response) => response.status === 200 || response.status === 201,
        "verification remains pending facial confirmation": (response) => response.json("status") === "qr_verified",
    });

    sleep(0.1);
}
