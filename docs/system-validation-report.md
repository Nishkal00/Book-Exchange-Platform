# System Validation Report

| Item | Value |
| :--- | :--- |
| Date | 04 Nov 2026 14:52 |
| Target | `http://localhost:8001` |
| Method | `python backend/scripts/system_validation.py` (public API only, fresh users) |
| Result | **28 of 28 checks passed** |

## Checks

| # | Step | Requirement | Test case | Expected | Actual | Result |
| ---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Health endpoint responds | NF-002 | TC-OPS-01 | 200 ok | 200 | PASS |
| 2 | Register three users | F-001 | TC-AUTH-01 | 201 each | 201,201,201 | PASS |
| 3 | Login returns a token | F-002 | TC-AUTH-03 | 200 + token | 200 | PASS |
| 4 | Wrong password is rejected | F-002 / SR-006 | TC-AUTH-04 | 401 | 401 | PASS |
| 5 | View profile | F-004 | TC-PRF-01 | 200 + email | 200 | PASS |
| 6 | Create listing | F-010 | TC-LST-01 | 201 | 201 | PASS |
| 7 | Search finds the listing | F-011 | TC-LST-03 | listing in results | 1 | PASS |
| 8 | Create borrow request | F-020 | TC-REQ-01 | 201 OPEN | 201 | PASS |
| 9 | Matching engine proposes the listing | F-022 | TC-MAT-01 | 1 ranked match | 1 | PASS |
| 10 | Lender receives a match notification | F-023 | TC-NOT-01 | MATCH_FOUND | ['MATCH_FOUND'] | PASS |
| 11 | Match list shows no contact details | SR-007 | TC-SEC-07 | no email/phone fields | none | PASS |
| 12 | Outsider cannot decide a match | SR-005 | TC-SEC-05 | 403 | 403 | PASS |
| 13 | Mutual acceptance creates an exchange | F-024 | TC-MAT-04 | exchangeId set | 36 | PASS |
| 14 | Outsider cannot read partner contact | SR-007 | TC-SEC-07 | 403 or 404 | 403 | PASS |
| 15 | Participant can read partner contact after acceptance | SR-007 | TC-SEC-07 | 200 + email | 200 | PASS |
| 16 | Handover needs a due date | F-025 | TC-EXC-01 | 409 | 409 | PASS |
| 17 | Past due date is rejected | F-025 | TC-EXC-01 | 422 | 422 | PASS |
| 18 | Agreed future due date is recorded | F-025 | TC-EXC-01 | 200 | 200 | PASS |
| 19 | Only the lender can confirm handover | F-025 | TC-EXC-01 | 403 | 403 | PASS |
| 20 | Lender confirms handover | F-025 | TC-EXC-01 | ON_LOAN | ON_LOAN | PASS |
| 21 | Cancel after handover is rejected | F-025 | TC-EXC-01 | 409 | 409 | PASS |
| 22 | First return confirmation keeps ON_LOAN | F-026 | TC-EXC-02 | ON_LOAN | ON_LOAN | PASS |
| 23 | Repeated confirmation is idempotent | F-026 | TC-EXC-02 | one RETURN_CONFIRMED | 1 | PASS |
| 24 | Second confirmation completes the return | F-026 | TC-EXC-02 | RETURNED | RETURNED | PASS |
| 25 | Listing is available again | F-026 | TC-EXC-02 | AVAILABLE | ['AVAILABLE'] | PASS |
| 26 | History shows the exchange only to participants | F-030 | TC-HIS-01 | borrower yes, outsider no | borrower=True, outsider=False | PASS |
| 27 | Anonymous access is refused | SR-002 / SR-005 | TC-SEC-02 | 401 or 403 | 401 | PASS |
| 28 | Logout revokes the token | F-003 / SR-002 | TC-AUTH-05 | 204 then 401 | 204 then 401 | PASS |

## Not covered by this run

Features not part of the scripted flow (ratings F-031, admin moderation F-040, response
time targets NF-001/NF-005, uptime NF-002, usability NF-003) are verified by their own
reports and tests; see the RTM.
