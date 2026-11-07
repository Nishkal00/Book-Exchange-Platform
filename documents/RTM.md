
# Requirements Traceability Matrix (RTM)

## Book Exchange Platform

| Document Detail | Value |
|---|---|
| Project | Book Exchange Platform |
| Document | Requirements Traceability Matrix |
| Version | 1.2 |
| Date | 7 November 2026 |
| Source Documents | SRS v1.0, SAD v1.0, Test Plan v1.1 |
| Deployment | Render |
| Verified Code Commit | `b3b9eec` (main, 6 Nov 2026) |
| CI Workflow Runs | #46 (31 Oct), every PR since |

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
| F-001 | TC-AUTH-01, TC-AUTH-02 | A | All linked test cases pass (see section 4). |
| F-002 | TC-AUTH-03, TC-AUTH-04 | A | All linked test cases pass (see section 4). |
| F-003 | TC-AUTH-05, TC-AUTH-06 | A | Backend revokes all tokens at logout; the website Sign out now calls the API (BEP-38). |
| F-004 | TC-PRF-01, TC-PRF-02 | A | All linked test cases pass (see section 4). |
| F-010 | TC-LST-01, TC-LST-02 | A | All linked test cases pass (see section 4). |
| F-011 | TC-LST-03, TC-LST-04, TC-LST-08 | A | All linked test cases pass (see section 4). |
| F-012 | TC-LST-05 | A | All linked test cases pass (see section 4). |
| F-013 | TC-LST-06, TC-LST-07 | A | Active-exchange guard verified with a real database exchange (TC-LST-07). |
| F-020 | TC-REQ-01 | A | All linked test cases pass (see section 4). |
| F-021 | TC-REQ-02 | A | All linked test cases pass (see section 4). |
| F-022 | TC-MAT-01, TC-MAT-02, TC-MAT-03 | A | Ranking, exclusions, locking and re-match verified in test_matching.py. |
| F-023 | TC-NOT-01 | A | All linked test cases pass (see section 4). |
| F-024 | TC-MAT-04 | A | All linked test cases pass (see section 4). |
| F-025 | TC-EXC-01 | A | Cancelling before handover reopens the borrow request (design choice, see Test Plan v1.1). |
| F-026 | TC-EXC-02 | A | All linked test cases pass (see section 4). |
| F-030 | TC-HIS-01 | A | All linked test cases pass (see section 4). |
| F-031 | TC-RAT-01 | A | Rating is submitted for the partner of a RETURNED exchange; averages recomputed. |
| F-040 | TC-ADM-01, TC-ADM-02 | A | Deactivate and hide write audit rows; admins read them through GET /api/v1/admin/audit (BEP-45). |
| NF-001 | TC-PERF-01 | A | p90 1.3218 s at 50 concurrent users (docs/perf-sprint1.md). |
| NF-002 | TC-OPS-01 | A | 99.33% availability, 2 Nov to 7 Nov 19:39 IST (target 99%); one 503 outage of 55 min 53 s on 4 Nov disclosed (docs/tls-uptime-sprint2.md, BEP-35). |
| NF-003 | TC-UX-01 | A | 360px: no horizontal scroll on 9 views; create listing 3 clicks, search 2 clicks; labelled inputs; keyboard sign-in; readable errors (docs/ux-evidence-sprint2.md, BEP-50). |
| NF-004 | TC-CI-01 | A | Deliberate failing test turned the required backend check red and fixing it restored green; docker and deploy did not run on the PR (docs/ci-gate-evidence-sprint2.md, BEP-51). |
| NF-005 | TC-PERF-02 | A | p95 1.3594 s (docs/perf-sprint2.md). |
| NF-006 | TC-PORT-01 | N | Not run: Docker was not available to the team before the Sprint 2 deadline. Recorded as DEV-10 in DEVIATIONS.md. |
| SR-001 | TC-SEC-01 | A | All linked test cases pass (see section 4). |
| SR-002 | TC-AUTH-05, TC-AUTH-06, TC-SEC-02 | A | All linked test cases pass (see section 4). |
| SR-003 | TC-SEC-03 | A | SSL Labs grade A; TLS 1.2 and 1.3; CORS limited to the frontend; no secrets in the repository. HSTS header not sent (SEC-01, optional). |
| SR-004 | TC-SEC-04 | A | All linked test cases pass (see section 4). |
| SR-005 | TC-PRF-02, TC-SEC-05 | A | All linked test cases pass (see section 4). |
| SR-006 | TC-SEC-06 | A | Throttling at the API returns 429 with Retry-After after five failures. |
| SR-007 | TC-SEC-07 | A | Contact is disclosed only to participants of an active exchange; cancellation revokes it. |

Summary: 30 Accepted, 0 Failed, 1 Not Run (NF-006), of 31 requirements.

## 4. Test Case Results

Executed on `b3b9eec` (backend suite: 177 tests passed, statement coverage 94.8%, branch coverage 83.7%, combined 92.7%; system validation 28/28 passed on a local PostgreSQL stack, 6 Nov 2026). Reports: `docs/unit-test-report.md`, `docs/coverage-report.md`, `docs/branch-coverage-report.md`, `docs/system-validation-report.md`, `docs/perf-sprint1.md`, `docs/perf-sprint2.md`, `docs/tls-uptime-sprint2.md`, `docs/ux-evidence-sprint2.md`, `docs/ci-gate-evidence-sprint2.md`.

| Test case | Requirement | Result | Evidence |
|---|---|---|---|
| TC-AUTH-01 | F-001 | Pass | test_auth_register.py::test_registration_success; system validation step 2 |
| TC-AUTH-02 | F-001 | Pass | test_auth_register.py (unapproved domain, weak password); test_security_evidence.py::test_tc_auth_02_duplicate_domain_weak_password_and_empty_name |
| TC-AUTH-03 | F-002 | Pass | test_auth_login.py::test_login_success_returns_30_minute_jwt; system validation step 3 |
| TC-AUTH-04 | F-002 | Pass | test_auth_login.py::test_login_invalid_credentials_are_identical; system validation step 4 |
| TC-AUTH-05 | F-003, SR-002 | Pass | test_auth_logout.py::test_tc_auth_05_* (3 tests); system validation step 28; UI Sign out calls the API (BEP-38, PR #22) |
| TC-AUTH-06 | F-003, SR-002 | Pass | test_auth_logout.py::test_tc_auth_06_* (4 tests); test_auth_login.py expired and stale-version tests |
| TC-PRF-01 | F-004 | Pass | test_profile.py::test_tc_prf_01_*, test_update_my_profile_success_and_persistence; system validation step 5 |
| TC-PRF-02 | F-004, SR-005 | Pass | test_profile.py::test_tc_prf_02_update_my_profile_rejects_protected_fields |
| TC-LST-01 | F-010 | Pass | test_listings.py::test_tc_lst_01_* (2 tests); system validation step 6 |
| TC-LST-02 | F-010 | Pass | test_listings.py::test_tc_lst_02_* (2 tests) |
| TC-LST-03 | F-011 | Pass | test_listings.py::test_tc_lst_03_search_filters_and_availability; system validation step 7 |
| TC-LST-04 | F-011 | Pass | test_listings.py::test_tc_lst_04_pagination_limits_and_empty_results |
| TC-LST-05 | F-012 | Pass | test_listings.py::test_tc_lst_05_update_listing_owner_status_and_lifecycle |
| TC-LST-06 | F-013 | Pass | test_listings.py::test_tc_lst_06_delete_idle_listing_and_exclusion |
| TC-LST-07 | F-013 | Pass | test_listings.py::test_tc_lst_07_active_exchange_delete_guard; test_matching.py::test_real_active_exchange_delete_guard (real exchange, no mock) |
| TC-LST-08 | F-011 | Pass | test_listings.py::test_tc_lst_08_my_listings_isolation_and_statuses |
| TC-REQ-01 | F-020 | Pass | test_requests.py (create by ISBN and title, empty and double criteria 422, duplicate 409, other user independent); system validation step 8 |
| TC-REQ-02 | F-021 | Pass | test_matching.py::test_borrow_request_duplicate_and_cancel_guards (owner cancel 200, non-owner 403, active exchange 409); PR #29 |
| TC-MAT-01 | F-022 | Pass | test_matching.py::test_tc_mat_01_fixed_candidate_fixtures_and_exclusions; system validation step 9 |
| TC-MAT-02 | F-022 | Pass | test_matching.py::test_tc_mat_02_simultaneous_mutual_acceptances |
| TC-MAT-03 | F-022 | Pass | test_matching.py::test_tc_mat_03_decline_expire_recompute_and_deterministic_ties |
| TC-MAT-04 | F-024 | Pass | test_match_decision.py::test_tc_mat_04_* (7 tests); system validation step 13 |
| TC-NOT-01 | F-023 | Pass | test_notifications.py::test_tc_not_01_* (7 tests); test_matching.py notification tests; test_exchange_return.py notification test; system validation step 10 |
| TC-EXC-01 | F-025 | Pass | test_exchanges.py (due date, handover, cancel rules, history); system validation steps 16-21 |
| TC-EXC-02 | F-026 | Pass | test_exchange_return.py (9 tests); system validation steps 22-25 |
| TC-HIS-01 | F-030 | Pass | test_exchanges.py::test_exchange_history_* (6 tests); system validation step 26 |
| TC-RAT-01 | F-031 | Pass | test_ratings.py (rate after return, before return rejected, duplicate, range, non-integer, outsider, anonymous, average recomputed); the ratee is derived from the exchange and the database forbids rater = ratee |
| TC-ADM-01 | F-040 | Pass | test_admin.py (deactivate with reason, hide listing, student 403, missing reason 422, deactivated user's token revoked) |
| TC-ADM-02 | F-040 | Pass | test_admin.py (admin 200 with items and total, student 403, anonymous 401, only allowed fields exposed, pagination and newest first); BEP-45, PR #72 |
| TC-SEC-01 | SR-001 | Pass | test_auth_register.py (bcrypt hash stored, no hash in response); test_security_evidence.py::test_tc_sec_01_*. Log capture check not automated. |
| TC-SEC-02 | SR-002 | Pass | test_auth_login.py and test_auth_logout.py (tampered, wrong secret, expired, stale version); test_security_evidence.py (alg none, garbage token, missing token, inactive user) |
| TC-SEC-03 | SR-003 | Pass | docs/tls-uptime-sprint2.md: SSL Labs grade A, TLS 1.2 and 1.3 only, HTTP opens on HTTPS, no secrets in repo; test_security_evidence.py::test_tc_sec_03_cors_allows_configured_origin_only |
| TC-SEC-04 | SR-004 | Pass | test_listings.py::test_tc_sec_04_sql_and_html_injection_safety |
| TC-SEC-05 | SR-005 | Pass | test_listings.py::test_tc_sec_05_*, test_listing_privilege_escalation_rejected; system validation step 12 |
| TC-SEC-06 | SR-006 | Pass | test_login_rate_limit.py (5 tests, rolling window); test_security_evidence.py::test_tc_sec_06_* (429 with Retry-After, success clears failures) |
| TC-SEC-07 | SR-007 | Pass | test_match_decision.py::test_tc_sec_07_* (4 tests); test_match_list.py; test_exchanges.py contact tests; system validation steps 11, 14, 15 |
| TC-PERF-01 | NF-001 | Pass | docs/perf-sprint1.md: p90 1.3218 s (target <= 2 s), 0 errors, 50 users |
| TC-PERF-02 | NF-005 | Pass | docs/perf-sprint2.md: p95 1.3594 s (target <= 2 s), 1,000 requests, 10,000 listings, 0 fatal errors |
| TC-OPS-01 | NF-002 | Pass | docs/tls-uptime-sprint2.md: 99.33% for 2 Nov 00:00 to 7 Nov 19:39 IST (target >= 99%), one disclosed 503 outage on 4 Nov (55 min 53 s); docs/uptime-export.csv, docs/uptime-1.png, docs/uptime-2.png (BEP-35) |
| TC-UX-01 | NF-003 | Pass | docs/ux-evidence-sprint2.md with screenshots in docs/ux-evidence/: no horizontal scroll on 9 views at 360px, create listing 3 clicks, search 2 clicks (limit 5), all inputs labelled, keyboard sign-in works, errors readable (BEP-50). Run on a local build of main 46c729c, Chromium only. |
| TC-CI-01 | NF-004 | Pass | docs/ci-gate-evidence-sprint2.md with screenshots in docs/ci-gate-evidence/: throwaway PR #76 with a deliberate failing test turned backend red (docker and deploy skipped), the restore commit turned all required checks green, PR #76 closed without merging; review gate shown on PR #75 (BEP-51) |
| TC-PORT-01 | NF-006 | Not run | Fresh clone and `docker compose up --build` were not run: Docker was not available to the team before the deadline. A suspected port mismatch (compose maps the backend to host port 8001, documentation and the frontend expect 8000) is recorded as DEV-09 and DEV-10. |

Totals: 41 Pass, 0 Fail, 1 Not run (42 test cases).

## 5. Deployment and CI Evidence

| Item | Evidence |
|---|---|
| Deployment platform | Render |
| Frontend | https://bep-frontend.onrender.com/ |
| Backend health endpoint | https://bep-backend.onrender.com/health |
| API documentation | https://bep-backend.onrender.com/docs |
| Deployment path | Merge to `main`, CI passes, deploy hook triggers Render, `/health` checked |
| Live API contains Sprint 2 endpoints | Observed 5 Nov 2026 (exchanges, ratings, return, admin) |
| Required PR checks | backend (lint, tests, migrations), frontend (build), docker (build images) |
| Coverage gate | >= 70% (measured 92.7% combined, branch coverage on) |

## 6. Manual Verification Summary

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

## 7. Outstanding Verification

| Item | Owner | Status on 7 Nov 2026 |
|---|---|---|
| TC-OPS-01: UptimeRobot export for 2-7 Nov (BEP-35) | Nishkal | Done, Pass |
| TC-UX-01: click counts, keyboard access, error readability at 360px (BEP-50) | Nishkal | Done, Pass |
| TC-CI-01: deliberate failing branch and the blocked gate (BEP-51) | Nishkal | Done, Pass |
| TC-PORT-01: fresh clone and `docker compose up --build` on a clean machine | Teammate | Not run; recorded in DEVIATIONS.md (DEV-10) and carried to the next sprint |
| Re-run `generate_test_reports.py` and `system_validation.py` on the final commit, then update this RTM | Nishkal | Done in BEP-49 (PR #73) |

## 8. Evidence Management

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

## 9. Acceptance and Review

A requirement must not be marked Accepted until all associated test cases have passed and the supporting evidence has been reviewed.

This document is a working verification record and does not represent final project acceptance or formal sign-off.

| Review Item | Status |
|---|---|
| RTM prepared | Done (v1.2, 7 Nov 2026) |
| Test execution recorded | Done (41 pass, 1 not run, 0 failed) |
| Evidence reviewed | Pending |
| Team review | Pending |
| Final acceptance | Pending |
