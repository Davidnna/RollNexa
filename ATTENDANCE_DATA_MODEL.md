# RollNexa attendance data model — 0.6.0

## Purpose

The attendance foundation separates a lecturer's scheduled class session from a student's verified attendance record. A session can exist without any attendance records. A record represents a student who has successfully completed both required identity checks.

## Entities

### AttendanceSession

`AttendanceSession` belongs to one `CourseOffering` and is created by an authenticated lecturer who has an active `CourseLecturerAssignment` for that offering.

Important fields:

- `offering`: the programme-specific course offering being taught.
- `title`: optional lecturer label, such as Lecture 1 or Week 3 tutorial.
- `starts_at`, `ends_at`: the valid time window for the session.
- `status`: scheduled, active, closed or cancelled.
- `created_by`: lecturer account that created the session.
- `activated_at`, `closed_at`, `cancelled_at`: lifecycle audit timestamps.
- `activated_by`, `closed_by`, `cancelled_by`: lecturer accounts responsible for each transition.
- `notes`: optional lecturer-only operational notes.

A database check constraint enforces `ends_at > starts_at`. Another check constraint enforces valid status/timestamp combinations. Application validation rejects overlapping non-cancelled sessions for the same course offering. Session creation locks the course offering row while validating and saving, serialising concurrent session creation for that offering.

### AttendanceRecord

`AttendanceRecord` links one `AttendanceSession` to one student `UserProfile`.

Important fields:

- `session`: attendance session.
- `student`: student account profile.
- `qr_verified_at`: time QR verification succeeded.
- `face_verified_at`: time facial verification succeeded.
- `recorded_at`: time the final attendance record was committed.

A unique database constraint permits at most one record for each `(session, student)` pair. Database checks prevent either verification timestamp from occurring after `recorded_at` and require facial verification to occur at or after QR verification. The model does not store raw facial images, face embeddings or other biometric samples.

## Relationships

- One `CourseOffering` can have many `AttendanceSession` records.
- One lecturer account can create many `AttendanceSession` records.
- One `AttendanceSession` can have many `AttendanceRecord` records.
- One student profile can have many `AttendanceRecord` records across different sessions.
- A student must have a current `CourseRegistration` for the session's course offering before a record can be created.

## Session lifecycle

`scheduled -> active -> closed`

`scheduled -> cancelled`

An active session can only be activated during its configured time window. A scheduled session can be cancelled. An active session is closed explicitly by an assigned lecturer. A session whose end time has passed is no longer open for attendance recording, even if its status has not yet been changed from active; the lecturer can close it to finalise its state.

## Dual-verification invariant

RollNexa's selected policy is **QR Code AND Facial Recognition**. Attendance must not be recorded if either verification fails or is missing.

The `record_verified_attendance` service therefore requires:

1. `qr_verified=True` and `face_verified=True` from the trusted server-side verification orchestration layer.
2. Both successful verification timestamps, with facial verification occurring after QR verification.
3. An active session and timestamps inside the session window.
4. An active student account whose current programme and level match the offering, with a current course registration.
5. At least one active lecturer assignment for the course offering.
6. No existing attendance record for that student and session.

The service is the integration boundary for the future QR and face-recognition components. It does not itself decode QR tokens, run a face model or perform liveness detection; those verifiers must be implemented and called before the service is invoked. The 0.6.0 web interface does not expose student check-in yet.
