
# Project Deviations and Limitations

## Book Exchange Platform

| Document Detail | Value |
|---|---|
| Project | Book Exchange Platform |
| Document | Deviations and Limitations |
| Version | 1.0 |
| Date | 31 October 2026 |
| Reference Documents | SRS v1.0, SAD v1.0, Test Plan v1.0 |

---

## 1. Purpose

This document records known implementation deviations, testing limitations, and observations identified during Sprint 1 of the Book Exchange Platform.

It provides transparency between the planned architecture, implemented functionality, and verified test results.

## 2. Planned Implementation Deviations

The SAD identifies the following deviations from the original design.

| ID | Area | Planned Deviation | Description | Status |
|---|---|---|---|---|
| DEV-01 | Rate Limiting | In-memory rate limiter | Sprint 1 uses an in-memory rate limiter as a temporary implementation instead of a distributed rate-limiting mechanism. | Planned limitation; current implementation requires confirmation |
| DEV-02 | Exchange Workflow | Active-exchange stub | Sprint 1 includes a temporary active-exchange implementation that requires further review and completion. | Planned limitation; current implementation requires confirmation |

These items are documented in SAD Section 4.5 and its planned deviations.

## 3. Testing Limitations

| ID | Area | Observation | Impact | Follow-up |
|---|---|---|---|---|
| TEST-01 | Frontend Testing | Dedicated automated UI tests have not been demonstrated in the available CI evidence. | Manual browser verification is being used for the current deployment checks. | Add automated frontend tests. |
| TEST-02 | Responsive Testing | The 360px Browse Books layout and horizontal overflow were verified. Keyboard accessibility and validation-error readability remain unverified. | Complete NF-003 acceptance is pending. | Finish TC-UX-01. |
| TEST-03 | Security Testing | All security test cases have not been executed and evidenced. | Security requirements cannot yet be marked Accepted. | Execute applicable TC-SEC tests. |
| TEST-04 | CI Negative-Gate Testing | Successful CI execution and deployment were observed, but all deliberate failure scenarios have not been demonstrated. | Full TC-CI-01 acceptance remains pending. | Execute the negative-gate test scenarios. |

## 4. CI/CD Observations

| ID | Area | Observation | Impact | Follow-up |
|---|---|---|---|---|
| CI-01 | GitHub Actions | Workflow run #46 completed successfully and deployment was triggered. | Positive CI/CD execution observed. | Retain workflow evidence. |
| CI-02 | GitHub Actions | Node.js 20 deprecation warnings were displayed for GitHub Actions. | Maintenance warning; not a workflow failure. | Review action versions and Node.js runtime compatibility. |

## 5. Deployment Verification

The following deployment observations were recorded on 31 October 2026:

- Frontend deployed URL was accessible.
- Backend health endpoint returned `{"status":"ok"}`.
- Render deployment was triggered.
- Backend health check succeeded after the first attempt.
- Registration, login, listing management, and profile operations were manually exercised.

These observations do not independently establish that every SRS requirement has been accepted.

## 6. Resolution and Follow-up Plan

| Item | Planned Action |
|---|---|
| DEV-01 | Review rate-limiting implementation and deployment suitability. |
| DEV-02 | Review and complete the active-exchange workflow. |
| TEST-01 | Introduce automated frontend tests where applicable. |
| TEST-02 | Complete responsive, keyboard and validation checks. |
| TEST-03 | Execute and document security tests. |
| TEST-04 | Verify CI failure gates and deployment restrictions. |
| CI-02 | Review GitHub Actions runtime deprecation warnings. |

Unfinished items must be assigned to a future sprint with appropriate Jira tracking.

## 7. Review and Approval

| Review Item | Status |
|---|---|
| Known deviations documented | In Progress |
| Implementation details confirmed | Pending |
| Team review | Pending |
| Follow-up tasks assigned | Pending |
| Final approval | Pending |

This document is a working record. It does not represent formal approval of unresolved deviations.
