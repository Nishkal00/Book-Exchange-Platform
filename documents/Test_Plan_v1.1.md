# Test Plan v1.1

## Book Exchange Platform

| Field | Value |
|---|---|
| Version | 1.1 (supersedes v1.0 of 27 October 2026) |
| Date | 5 November 2026 |
| Code commit tested | `653560e` (main) |
| Related | `documents/RTM.md` v1.1, `documents/DEVIATIONS.md` |

## 1. Change log from v1.0

| Change | Reason |
|---|---|
| Test case list and requirement mapping unchanged (42 test cases, 31 requirements) | Scope did not change in Sprint 2 |
| Added an execution record (section 3) | Course requires tests executed per the plan |
| Branch coverage turned on in the coverage configuration | Branch Coverage report requirement |
| Added `backend/tests/test_security_evidence.py` | Automates TC-SEC-01, TC-SEC-02, TC-SEC-03, TC-SEC-06 and TC-AUTH-02 checks that were manual |
| Added `backend/scripts/system_validation.py` (28 checks over the public API) | System validation report |
| Added `backend/scripts/generate_test_reports.py` | Reproducible unit, coverage and branch coverage reports |
| Performance and TLS evidence moved into `docs/` | Reports required in `docs/` |

## 2. Execution summary

| Item | Result |
|---|---|
| Backend automated tests | 172 passed, 0 failed |
| Statement coverage | 94.6% (gate 70%) |
| Branch coverage | 83.9% (260 of 310 branches); combined statement and branch 92.6% |
| System validation | 28 of 28 checks passed |
| Test cases | 37 Pass, 1 Fail, 4 Not run (of 42) |
| Requirements | 26 Accepted, 1 Failed (F-040), 4 Not run (NF-002, NF-003, NF-004, NF-006) |

## 3. Execution record

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
| TC-ADM-02 | F-040 | FAIL | No endpoint exists to read the audit log (only writes). Tracked as BEP-45; see Test Plan v1.1 section 4. |
| TC-SEC-01 | SR-001 | Pass | test_auth_register.py (bcrypt hash stored, no hash in response); test_security_evidence.py::test_tc_sec_01_*. Log capture check not automated. |
| TC-SEC-02 | SR-002 | Pass | test_auth_login.py and test_auth_logout.py (tampered, wrong secret, expired, stale version); test_security_evidence.py (alg none, garbage token, missing token, inactive user) |
| TC-SEC-03 | SR-003 | Pass | docs/tls-uptime-sprint2.md: SSL Labs grade A, TLS 1.2 and 1.3 only, HTTP opens on HTTPS, no secrets in repo; test_security_evidence.py::test_tc_sec_03_cors_allows_configured_origin_only |
| TC-SEC-04 | SR-004 | Pass | test_listings.py::test_tc_sec_04_sql_and_html_injection_safety |
| TC-SEC-05 | SR-005 | Pass | test_listings.py::test_tc_sec_05_*, test_listing_privilege_escalation_rejected; system validation step 12 |
| TC-SEC-06 | SR-006 | Pass | test_login_rate_limit.py (5 tests, rolling window); test_security_evidence.py::test_tc_sec_06_* (429 with Retry-After, success clears failures) |
| TC-SEC-07 | SR-007 | Pass | test_match_decision.py::test_tc_sec_07_* (4 tests); test_match_list.py; test_exchanges.py contact tests; system validation steps 11, 14, 15 |
| TC-PERF-01 | NF-001 | Pass | docs/perf-sprint1.md: p90 1.3218 s (target <= 2 s), 0 errors, 50 users |
| TC-PERF-02 | NF-005 | Pass | docs/perf-sprint2.md: p95 1.3594 s (target <= 2 s), 1,000 requests, 10,000 listings, 0 fatal errors |
| TC-OPS-01 | NF-002 | Not run | The 2-7 Nov measurement window is still open. Export the UptimeRobot report on 7 Nov and fill docs/tls-uptime-sprint2.md (BEP-35). |
| TC-UX-01 | NF-003 | Not run | 360px layout verified on 31 Oct. Click count (<= 5 for create listing and search), keyboard access and error readability not yet recorded. |
| TC-CI-01 | NF-004 | Not run | CI gates are active (PRs waited for the three required checks; coverage gate 70%, overall 93%). The deliberate failing-branch demonstration has not been run. |
| TC-PORT-01 | NF-006 | Not run | Fresh-clone docker compose run not yet recorded. |

## 4. Failures and open items

| Item | Detail | Action |
|---|---|---|
| TC-ADM-02 (Fail) | Audit rows are written on deactivate and hide, but no endpoint reads them | BEP-45 (Abhiram): `GET /api/v1/admin/audit`, admin 200, student 403, pagination |
| TC-OPS-01 (Not run) | Uptime window 2 to 7 Nov still open | Export UptimeRobot report on 7 Nov (BEP-35) |
| TC-UX-01 (Not run) | Click count, keyboard access and error readability not recorded | Record with screenshots before 7 Nov |
| TC-CI-01 (Not run) | No deliberate failing-branch run | Run once and screenshot the blocked PR |
| TC-PORT-01 (Not run) | Fresh-clone docker compose not recorded | Run on a clean machine |

## 5. Deviations found during execution

These are in addition to those in `documents/DEVIATIONS.md` v1.0 and are to be merged into the final deviations document (BEP-37).

| ID | Deviation | Impact |
|---|---|---|
| DEV-03 | No endpoint to read the audit log (until BEP-45) | TC-ADM-02 fails |
| DEV-04 | Extra endpoints `GET /api/v1/requests` and `GET /api/v1/matches` beyond SAD v1.0 | Needed by the Requests screen; additive |
| DEV-05 | Cancelling an exchange before handover reopens the borrow request to OPEN | Design choice, listing returns to AVAILABLE |
| DEV-06 | HSTS header not sent by the backend or the static host | TLS grade A is unaffected; optional hardening |
| DEV-07 | Jira used for backlog and board instead of a GitHub Project | Pending BEP-43 part 2 (link or instructor confirmation) |
| DEV-08 | Automated frontend tests not written (TEST-01 in v1.0 remains) | Frontend verified manually and by an end-to-end browser run |

## 6. Exit criteria for the final run

1. All Sprint 2 pull requests merged and reviewed.
2. `generate_test_reports.py` and `system_validation.py` re-run on the final commit.
3. RTM statuses updated for TC-ADM-02 and the four Not run cases, or each recorded as a deviation.
