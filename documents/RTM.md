
# Requirements Traceability Matrix (RTM)

## Book Exchange Platform

| Document Detail | Value |
|---|---|
| Project | Book Exchange Platform |
| Document | Requirements Traceability Matrix |
| Version | 1.0 |
| Date | 31 October 2026 |
| Source Documents | SRS v1.0, SAD v1.0, Test Plan v1.0 |
| Deployment | Render |
| Verified Deployment Commit | `de83490` |
| CI Workflow Run | #46 |

---

## 1. Purpose

This document maps the requirements specified in the Software Requirements Specification (SRS) to their corresponding test cases in the Test Plan.

It records test execution status, observed results, supporting evidence and outstanding verification activities.

## 2. Status Definitions

| Status | Meaning |
|---|---|
| N | Not Run |
| A | Accepted — all linked test cases passed |
| F | Failed |
| B | Blocked |

A requirement can be marked Accepted only after every linked test case passes.

Partially executed requirements remain N until all applicable tests are completed.

## 3. Requirement Traceability

| Requirement ID | Linked Test Cases | Status | Execution Remarks |
|---|---|---|---|
| F-001 | TC-AUTH-01, TC-AUTH-02, TC-SEC-01 | N | Deployed registration accepted `@stu.pes.edu` and rejected `@gmail.com`. Other linked tests pending. |
| F-002 | TC-AUTH-03, TC-AUTH-04, TC-SEC-02 | N | Valid login verified on deployed application. Remaining linked tests pending. |
| F-003 | TC-AUTH-05, TC-AUTH-06 | N | Not verified in this session. |
| F-004 | TC-PRF-01, TC-PRF-02 | N | Profile retrieval and update persistence manually verified. Complete linked test coverage pending. |
| F-010 | TC-LST-01, TC-LST-02, TC-SEC-04 | N | Deployed book listing successfully created and displayed. Remaining linked tests pending. |
| F-011 | TC-LST-03, TC-LST-04, TC-LST-08 | N | Listing edit functionality manually verified. Remaining linked tests pending. |
| F-012 | TC-LST-05, TC-SEC-05 | N | Availability changed from AVAILABLE to UNAVAILABLE and persisted after refresh. Security test pending. |
| F-013 | TC-LST-06, TC-LST-07, TC-SEC-05 | N | Delete confirmation dialog verified. Cancellation tested; actual deletion not verified. |
| NF-001 | TC-PERF-01 | N | Performance test not executed in this session. |
| NF-002 | TC-OPS-01 | N | Operations test not fully verified in this session. |
| NF-003 | TC-UX-01 | N | 360px layout and no horizontal overflow verified. Search empty state verified. Click-count, keyboard accessibility and validation-error checks remain pending. |
| NF-004 | TC-CI-01 | N | GitHub Actions workflow run #46 succeeded and deployment was triggered. Full negative-gate testing remains pending. |
| NF-006 | TC-PORT-01 | N | Portability test not executed in this session. |
| SR-001 | TC-SEC-01 | N | Security test not fully executed. |
| SR-002 | TC-SEC-02, TC-AUTH-05, TC-AUTH-06 | N | Security tests not fully executed. |
| SR-003 | TC-SEC-03 | N | Not verified in this session. |
| SR-004 | TC-SEC-04 | N | Not verified in this session. |
| SR-005 | TC-SEC-05, TC-PRF-02 | N | Not fully verified. |
| SR-006 | TC-SEC-06 | N | Not verified in this session. |
| SR-007 | TC-SEC-07 | N | Not verified in this session. |

## 4. Deployment and CI Evidence

| Item | Evidence |
|---|---|
| Deployment platform | Render |
| Frontend | https://bep-frontend.onrender.com/ |
| Backend health endpoint | https://bep-backend.onrender.com/health |
| API documentation | https://bep-backend.onrender.com/docs |
| Verified deployment commit | `de83490` |
| GitHub Actions workflow run | #46 |
| CI result | Successful |
| Backend health response | `{"status":"ok"}` |
| Deployment trigger | Render deploy triggered |
| Backend health check | Healthy after attempt 1 |

## 5. Manual Verification Summary

The following behaviours were observed on the deployed application on 31 October 2026:

1. Homepage loaded successfully.
2. Browse Books page loaded.
3. Search for Python displayed the empty state without an error.
4. Registration rejected an unapproved Gmail domain.
5. Registration using an approved `@stu.pes.edu` address succeeded.
6. Login using the registered account succeeded.
7. Authenticated Browse Books and My Listings pages loaded.
8. A Ramayana listing was created successfully.
9. Listing edit functionality worked.
10. Availability changed from AVAILABLE to UNAVAILABLE and persisted after refresh.
11. Delete confirmation dialog appeared; deletion was cancelled.
12. Profile information was retrieved and updated successfully.
13. Profile changes persisted after refresh.
14. Browse Books rendered at a 360px viewport.
15. Browser measurement returned a document width of 360px and no horizontal overflow.

## 6. Outstanding Verification

The following activities remain outstanding:

- Complete all linked authentication test cases.
- Verify duplicate registration and invalid-credential behaviour.
- Complete all listing and security test cases.
- Verify actual listing deletion if required by the test plan.
- Complete TC-UX-01 click-count verification for listing creation and search.
- Verify keyboard accessibility and validation-error readability.
- Execute the remaining performance, operations and portability tests.
- Complete CI negative-gate testing.
- Capture and commit test evidence.
- Review the final RTM with the team.

## 7. Evidence Management

Test evidence should be maintained in the project repository.

Suggested structure:

```text
documents/
    RTM.md

evidence/
    deployment/
    authentication/
    listings/
    profile/
    responsive/
    ci-cd/
```

Evidence should include relevant screenshots, test reports, workflow run references and commit identifiers.

Do not store passwords, JWTs, API secrets or other credentials in the evidence directory.

## 8. Acceptance and Review

A requirement must not be marked Accepted until all associated test cases have passed and the supporting evidence has been reviewed.

This document is a working verification record and does not represent final project acceptance or formal sign-off.

| Review Item | Status |
|---|---|
| RTM prepared | In Progress |
| Test execution recorded | In Progress |
| Evidence reviewed | Pending |
| Team review | Pending |
| Final acceptance | Pending |
