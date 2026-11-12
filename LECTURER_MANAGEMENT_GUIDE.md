# RollNexa lecturer management guide

## 1. Create a lecturer account

1. Sign in using the system administrator account.
2. Open **User management** and select **Create account**.
3. Choose **Lecturer** as the account role.
4. Enter the lecturer's name, email, institutional ID (if available), phone number and home department.
5. Create the account and securely provide the temporary password to the lecturer.
6. The lecturer must change the temporary password at first sign-in.

The lecturer's home department is an academic profile attribute. It does not limit which course offerings the lecturer may teach.

## 2. Review lecturer profiles

Open `/management/lecturers/`.

The directory supports search by lecturer identity, email, institutional ID or department, as well as department and account-status filters. Open **View profile** to review the lecturer's home department, active assignments and revoked assignment history. Use **Edit account** to update profile information.

## 3. Assign a lecturer from a course offering

1. Open **Course management**.
2. Open **Course offerings** and select the relevant offering.
3. In **Assigned lecturers**, choose an active lecturer and submit the assignment.
4. Review any cross-department indicator.

A lecturer whose home department differs from the course-owning department may still be assigned. RollNexa flags the relationship but does not block it or change the lecturer's home department. Multiple lecturers may be assigned to the same offering.

## 4. Use the central teaching-assignment register

Open `/management/teaching-assignments/`.

The page supports assignment creation, searching by lecturer/course/programme/department, and filtering active assignments, revoked history or all records. Use **Revoke assignment** to end an assignment while preserving the audit record.

## 5. Revoke and reassign

Revoking an assignment records the time and administrator. It does not delete the row. If the same lecturer needs to teach the same offering again later, create a new assignment. The previous assignment remains in history and the new assignment receives its own creation record.

Deactivating a lecturer account automatically revokes all of that lecturer's active assignments. If the account is later reactivated, assignments must be deliberately recreated by an administrator.

## 6. Lecturer workspace

Lecturers sign in at the normal RollNexa sign-in page. Their dashboard shows their active teaching assignments. **My teaching** lists assigned course offerings; **View class roster** opens registered students for that offering.

A lecturer cannot view a roster merely by knowing its URL. The server verifies that the lecturer has an active assignment to the offering.

## 7. Important operating rule

Keep course offerings closed to student registration until the institution has verified the curriculum, lecturer assignments and other academic setup. Lecturer assignment is not attendance marking. QR attendance sessions and attendance capture are separate later modules.
