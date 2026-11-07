
# Project Deviations and Limitations

## Book Exchange Platform

| Document Detail | Value |
|---|---|
| Project | Book Exchange Platform |
| Document | Deviations and Limitations |
| Version | 1.1 |
| Date | 7 November 2026 (v1.0 of 31 October 2026) |
| Reference Documents | SRS v1.0, SAD v1.0, Test Plan v1.0 and v1.1, RTM v1.2 |

---

## 1. Purpose

This document records known implementation deviations, testing limitations, and observations identified during Sprint 1 and Sprint 2 of the Book Exchange Platform.

It provides transparency between the planned architecture, implemented functionality, and verified test results.

## 2. Planned Implementation Deviations

The SAD identifies the following deviations from the original design.

| ID | Area | Planned Deviation | Description | Status |
|---|---|---|---|---|
| DEV-01 | Rate Limiting | In-memory rate limiter | Sprint 1 uses an in-memory rate limiter as a temporary implementation instead of a distributed rate-limiting mechanism. | Confirmed 7 Nov 2026: `backend/app/login_rate_limit.py` keeps failures in process memory (default 5 failed attempts per 15 minute window). It resets on restart and is not shared across instances. Accepted for the single-instance deployment |
| DEV-02 | Exchange Workflow | Active-exchange stub | Sprint 1 temporary active-exchange stub replaced in Sprint 2 (BEP-26) with real database queries against exchanges table and unique partial indexes. | Resolved in Sprint 2 (BEP-26) |

These items are documented in SAD Section 4.5 and its planned deviations.

Deviations found in Sprint 2 (also listed in Test Plan v1.1, section 5):

| ID | Area | Description | Status |
|---|---|---|---|
| DEV-03 | Admin audit | No endpoint to read the audit log existed until BEP-45 (PR #72, 6 Nov) | Resolved; TC-ADM-02 passes |
| DEV-04 | API | Extra endpoints `GET /api/v1/requests` and `GET /api/v1/matches` beyond SAD v1.0, needed by the Requests screen | Additive; accepted |
| DEV-05 | Exchange workflow | Cancelling an exchange before handover reopens the borrow request to OPEN and the listing returns to AVAILABLE | Design choice |
| DEV-06 | Transport security | HSTS header is not sent by the backend or the static host | TLS grade A unaffected; optional hardening |
| DEV-07 | Project management | Jira holds the backlog and board; a GitHub Project mirror was added and linked in the README (PR #71) | Resolved |
| DEV-08 | Frontend testing | Automated frontend tests not written (see TEST-01) | Verified manually and by an end-to-end browser run |
| DEV-09 | Docker Compose | `docker-compose.yml` maps the backend to host port 8001 while the README, `.env.example` and the frontend default expect `localhost:8000` | Suspected from code inspection, not confirmed by running compose. Proposed fix: map `8000:8000`, with its own card and reviewed PR |
| DEV-10 | Portability test | TC-PORT-01 (fresh clone and `docker compose up --build`) was not run because Docker was not available to the team before the deadline | NF-006 stays Not Run; carried to the next sprint |
| DEV-11 | Usability | Server wording "Value error," appears in the password error; input focus is a border colour and soft glow; colour contrast not measured; Chromium only | Does not fail NF-003; improvement items |

## 3. Testing Limitations

| ID | Area | Observation | Impact | Follow-up |
|---|---|---|---|---|
| TEST-01 | Frontend Testing | Dedicated automated UI tests have not been demonstrated in the available CI evidence. | Manual browser verification is being used for the current deployment checks. | Add automated frontend tests. |
| TEST-02 | Responsive Testing | The 360px layout, click counts, labels, keyboard access and error readability were verified on 7 Nov 2026 (docs/ux-evidence-sprint2.md, BEP-50). | NF-003 accepted. Chromium only; colour contrast not measured. | Resolved in Sprint 2. |
| TEST-03 | Security Testing | All seven TC-SEC test cases were executed and passed (RTM v1.2; TLS evidence in docs/tls-uptime-sprint2.md). Log capture for TC-SEC-01 is not automated. | SR-001 to SR-007 accepted. | Resolved in Sprint 2. |
| TEST-04 | CI Negative-Gate Testing | A deliberate failing test (PR #76, closed without merging) turned the required backend check red and was fixed on the same branch; review gate shown on PR #75 (docs/ci-gate-evidence-sprint2.md, BEP-51). Lint and build failure scenarios were not each demonstrated separately. | NF-004 accepted on the failing-test scenario. | Resolved in Sprint 2. |
| TEST-05 | Portability Testing | TC-PORT-01 was not run (see DEV-10). | NF-006 remains Not Run. | Run on a machine with Docker and decide DEV-09 in the next sprint. |

## 4. CI/CD Observations

| ID | Area | Observation | Impact | Follow-up |
|---|---|---|---|---|
| CI-01 | GitHub Actions | Workflow run #46 completed successfully and deployment was triggered. | Positive CI/CD execution observed. | Retain workflow evidence. |
| CI-02 | GitHub Actions | Node.js 20 deprecation warnings were displayed for GitHub Actions. | Maintenance warning; not a workflow failure. | Review action versions and Node.js runtime compatibility. |
| CI-03 | Uptime | UptimeRobot recorded one 503 outage on 4 Nov 2026 (20:47:52 to 21:43:45 IST, 55 min 53 s). Availability for 2 Nov to 7 Nov 19:39 IST was 99.33%. | NF-002 met; cause of the 503 not confirmed. | Check the Render events for that time. |

## 5. Deployment Verification

The following deployment observations were recorded on 31 October 2026 (Sprint 1):

- Frontend deployed URL was accessible.
- Backend health endpoint returned `{"status":"ok"}`.
- Render deployment was triggered.
- Backend health check succeeded after the first attempt.
- Registration, login, listing management, and profile operations were manually exercised.

These observations do not independently establish that every SRS requirement has been accepted. Sprint 2 verification is recorded in RTM v1.2 (41 test cases Pass, 1 Not run).

## 6. Resolution and Follow-up Plan

| Item | Planned Action |
|---|---|
| DEV-01 | Replace the in-memory limiter with a shared store if the backend is ever scaled beyond one instance. |
| DEV-02 | Done (BEP-26). |
| TEST-01 | Introduce automated frontend tests where applicable. |
| TEST-02 | Done (BEP-50). |
| TEST-03 | Done (RTM v1.2). |
| TEST-04 | Done for the failing-test scenario (BEP-51). |
| TEST-05, DEV-09, DEV-10 | Install Docker, run TC-PORT-01, decide on the compose port fix in the next sprint. |
| CI-02 | Review GitHub Actions runtime deprecation warnings. |

Unfinished items must be assigned to a future sprint with appropriate Jira tracking.

## 7. Review and Approval

| Review Item | Status |
|---|---|
| Known deviations documented | Done (v1.1, 7 Nov 2026) |
| Implementation details confirmed | Pending |
| Team review | Pending |
| Follow-up tasks assigned | Pending |
| Final approval | Pending |

This document is a working record. It does not represent formal approval of unresolved deviations.
