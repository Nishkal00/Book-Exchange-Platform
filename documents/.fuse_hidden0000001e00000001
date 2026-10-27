# Jira backlog preparation

Project: BEP | Board: 3

This is a local preparation file, not a Jira export or proof of issue creation. Local IDs below are not Jira issue keys. Use the real BEP keys returned by Jira.

Roles: Nishkal = DevOps; Abhiram = Auth; Manoj = Listings; Ravish = UI/docs/demo. Sprint 2 owners are proposals to confirm on 2 November. Account IDs still need to be matched to actual members.

Epics: Auth; Listings; Requests & Matching; Exchange; Admin; DevOps.

Workflow: To Do -> In Progress -> In Review -> Done. Estimate in story points before starting Sprint 1. Tests are part of stories, not additional estimated cards.

The newer detailed backlog groups related FR/SR requirements into stories. Follow those groups rather than duplicating security cards and counting effort twice.

Sprint 1: 27-31 October 2026, 17 stories, 55 points (Nishkal 13; Abhiram 12; Manoj 15; Ravish 15).
Sprint 2: 2-7 November 2026, 14 stories, 49 points; leave planned. Add matching/exchange UI acceptance to associated stories during Sprint 2 planning, with Ravish supporting; re-estimate openly if scope changes.

Sprint 1 goal: deliver reviewed, tested authentication and book-listing flows with a working deployment and repeatable setup.
Sprint 2 goal: complete request matching, exchanges, ratings, moderation and final acceptance evidence.

## Sprint 1

| Local ID | Story | Requirements | Owner | Points | Epic |
| --- | --- | --- | --- | --- | --- |
| S1-01 | Repo scaffold, Docker Compose, models and base migration | NF-006 | Nishkal | 5 | DevOps |
| S1-02 | CI pipeline with coverage, build and deployment stage | NF-004 | Nishkal | 5 | DevOps |
| S1-03 | Cloud deployment with HTTPS and health endpoint | NF-002 SR-003 | Nishkal | 3 | DevOps |
| S1-04 | Register | F-001 SR-001 | Abhiram | 3 | Auth |
| S1-05 | Login and JWT | F-002 SR-002 | Abhiram | 3 | Auth |
| S1-06 | Login rate limit | SR-006 | Abhiram | 2 | Auth |
| S1-07 | Logout and token expiry | F-003 | Abhiram | 2 | Auth |
| S1-08 | Profile view and edit | F-004 | Abhiram | 2 | Auth |
| S1-09 | Create listing | F-010 SR-004 | Manoj | 3 | Listings |
| S1-10 | Search listings with indexes and own-listings endpoint | F-011 NF-001 | Manoj | 5 | Listings |
| S1-11 | Update listing with ownership checks | F-012 SR-005 | Manoj | 2 | Listings |
| S1-12 | Soft-delete listing | F-013 | Manoj | 2 | Listings |
| S1-13 | Seed script and Locust performance test | NF-001 | Manoj | 3 | Listings |
| S1-14 | UI shell, routing, Register and Login pages | F-001 F-002 NF-003 | Ravish | 5 | Auth |
| S1-15 | UI Browse and Search page | F-011 | Ravish | 3 | Listings |
| S1-16 | UI My Listings and Profile pages | F-004 F-010 F-012 F-013 | Ravish | 5 | Listings |
| S1-17 | Demo video, RTM update and deviations | NF-003 | Ravish | 2 | DevOps |

## Sprint 2

| Local ID | Story | Requirements | Owner | Points | Epic |
| --- | --- | --- | --- | --- | --- |
| S2-01 | Create borrow request | F-020 | Manoj (proposed) | 3 | Requests & Matching |
| S2-02 | Cancel request | F-021 | Manoj (proposed) | 2 | Requests & Matching |
| S2-03 | Matching engine with scoring, locking and re-match | F-022 | Manoj (proposed) | 8 | Requests & Matching |
| S2-04 | In-app notifications | F-023 | Abhiram (proposed) | 3 | Exchange |
| S2-05 | Accept and decline match | F-024 | Manoj (proposed) | 5 | Requests & Matching |
| S2-06 | Exchange lifecycle and agreed due date | F-025 | Abhiram (proposed) | 5 | Exchange |
| S2-07 | Confirm return | F-026 | Abhiram (proposed) | 2 | Exchange |
| S2-08 | Exchange history | F-030 | Abhiram (proposed) | 2 | Exchange |
| S2-09 | Ratings | F-031 | Abhiram (proposed) | 3 | Exchange |
| S2-10 | Admin moderation and audit log | F-040 | Nishkal (proposed) | 5 | Admin |
| S2-11 | Contact privacy until mutual acceptance | SR-007 | Nishkal (proposed) | 3 | Admin |
| S2-12 | TLS verification and uptime report | SR-003 NF-002 | Nishkal (proposed) | 2 | DevOps |
| S2-13 | Matching performance benchmark | NF-005 | Nishkal (proposed) | 3 | Requests & Matching |
| S2-14 | Final documentation, deviations and demo video | ALL | Ravish (proposed) | 3 | DevOps |

## Story descriptions

### S1-01 [NF-006] Repo scaffold, Docker Compose, models and base migration

Owner: Nishkal
Epic: DevOps

Acceptance criteria
NF-006: A fresh checkout with documented environment values shall start backend, frontend and Postgres using docker compose up --build, apply migrations and pass registration/login/listing smoke tests without manual database edits.

Tests: TC-PORT-01

Scope and handoff: Scaffold must be merged by 28 Oct 12:00 IST; Abhiram reviews. Include token_version, department, deleted_at and pg_trgm. All backend routes use /api/v1.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-02 [NF-004] CI pipeline with coverage, build and deployment stage

Owner: Nishkal
Epic: DevOps

Acceptance criteria
NF-004: Each main-branch PR shall run lint, backend tests with >=70% application coverage, frontend production build and Docker build. Required checks and one independent approval gate merging. Auth coverage shall exceed 85% by the end of Sprint 1. Deployment runs only after successful main builds.

Tests: TC-CI-01

Scope and handoff: Keep tests within feature stories; coverage gate >=70% overall, Auth >85% by Sprint 1 close. Add required status checks only after real runs exist. Temporary deploy echo is not deployment completion.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-03 [NF-002 SR-003] Cloud deployment with HTTPS and health endpoint

Owner: Nishkal
Epic: DevOps

Acceptance criteria
NF-002: The deployed demo shall target >=99% successful /health probes during 2-7 November, measured every five minutes. Count sleep and unexpected outages as failures; disclose planned maintenance and missing measurements. This short-window target is not a monthly SLA.

SR-003: Deployed browser/API traffic shall use HTTPS and valid certificates; HTTP redirects to HTTPS without transmitting credentials. Verify TLS 1.2 or later. Restrict CORS to the configured frontend and keep secrets out of the repository.

Tests: TC-OPS-01, TC-SEC-03

Scope and handoff: Sprint 1 evidence is working HTTPS, health probe and monitor configured. Full NF-002 measurement and formal TLS report are Sprint 2; do not mark those requirements accepted early.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-04 [F-001 SR-001] Register

Owner: Abhiram
Epic: Auth

Acceptance criteria
F-001: The system shall register students using an allowed university email domain. Lowercase email; name 1-100 characters; password at least 8 characters with a letter and digit. Valid input returns 201; duplicate email 409; other domains 400; invalid fields 422. New users have the student role.

SR-001: The system shall store only salted bcrypt hashes and never return or log passwords or hashes. Reject passwords over 72 UTF-8 bytes to avoid bcrypt truncation. Public response schemas exclude secrets.

Tests: TC-AUTH-01, TC-AUTH-02, TC-SEC-01

Scope and handoff: Auth helpers get_current_user, security utilities and common errors must merge by 28 Oct 15:00 IST before dependent listing/UI work.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-05 [F-002 SR-002] Login and JWT

Owner: Abhiram
Epic: Auth

Acceptance criteria
F-002: The system shall authenticate email and password and issue a 30-minute JWT. Valid credentials return 200 with token and expiresIn=1800. Unknown email and wrong password both return the same 401 INVALID_CREDENTIALS.

SR-002: Protected routes shall verify JWT signature using an explicit HS256 allowlist, exp, subject, current active user and token_version. Tokens expire after 30 minutes; missing/invalid/expired tokens return 401. JWT_SECRET is supplied outside source control.

Tests: TC-AUTH-03, TC-AUTH-04, TC-AUTH-05, TC-AUTH-06, TC-SEC-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-06 [SR-006] Login rate limit

Owner: Abhiram
Epic: Auth

Acceptance criteria
SR-006: After five failed logins for the normalized email/client IP pair in 15 minutes, the next attempt returns 429 and Retry-After, including a correct password. Successful login before the limit clears failures. Expired failures are removed.

Tests: TC-SEC-06

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-07 [F-003] Logout and token expiry

Owner: Abhiram
Epic: Auth

Acceptance criteria
F-003: The system shall invalidate all existing tokens for the current user by atomically incrementing token_version on logout (204). Expired, tampered or version-mismatched tokens shall return 401 on protected endpoints.

Tests: TC-AUTH-05, TC-AUTH-06

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-08 [F-004] Profile view and edit

Owner: Abhiram
Epic: Auth

Acceptance criteria
F-004: The system shall allow an authenticated student to view and edit name, department and location. Saved changes appear in the next GET. Email, role, active and password_hash cannot be changed via this endpoint.

Tests: TC-PRF-01, TC-PRF-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-09 [F-010 SR-004] Create listing

Owner: Manoj
Epic: Listings

Acceptance criteria
F-010: The system shall create a listing for its authenticated owner, reuse a book by normalized unique ISBN, and set status AVAILABLE. Require title 1-200, author 1-150, location 1-100 and condition NEW/GOOD/FAIR/POOR. ISBN is 10 or 13 digits after hyphen removal in this course baseline. Valid input returns 201; invalid fields 422.

SR-004: The system shall validate request fields server-side and use ORM or bound SQL parameters. SQL-looking input must not alter query structure or expose unrelated rows; HTML content is rendered as text.

Tests: TC-LST-01, TC-LST-02, TC-SEC-04

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-10 [F-011 NF-001] Search listings with indexes and own-listings endpoint

Owner: Manoj
Epic: Listings

Acceptance criteria
F-011: The system shall publicly search AVAILABLE, non-deleted listings by title/author q, ISBN and location with pagination. Defaults page=1,size=20; size above 100 or page below 1 returns 422. Unknown searches return an empty items list. Authenticated /listings/mine returns only the caller's non-deleted listings including unavailable ones.

NF-001: The search API shall achieve p90 response time <=2 seconds with 50 concurrent users over a 1-minute run, ramping at 10 users/second, using 10,000 listings and about 2,000 books. Report errors, host resources and cold-start exclusions; do not claim success from an unrepresentative sample.

Tests: TC-LST-03, TC-LST-04, TC-LST-08, TC-PERF-01

Scope and handoff: Include GET /api/v1/listings/mine. API deadline is 29 Oct 18:00 IST; full search load measurements are in the seed/performance story.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-11 [F-012 SR-005] Update listing with ownership checks

Owner: Manoj
Epic: Listings

Acceptance criteria
F-012: The system shall allow the owner to partially update a listing, including AVAILABLE/UNAVAILABLE status. Non-owners receive 403; missing/deleted IDs 404. Reserved or on-loan listings cannot be changed to available or have their book changed.

SR-005: Every mutation shall enforce ownership or an explicit admin role server-side. Reject non-owner listing edits/deletes with 403 and profile privilege escalation with 422. Return only public fields in listing views.

Tests: TC-LST-05, TC-PRF-02, TC-SEC-05

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-12 [F-013] Soft-delete listing

Owner: Manoj
Epic: Listings

Acceptance criteria
F-013: The system shall soft-delete owner listings and return 204. Non-owners receive 403. A listing involved in an active exchange cannot be deleted (409 ACTIVE_EXCHANGE). Deleted listings are excluded from public and own-listing queries.

Tests: TC-LST-06, TC-LST-07, TC-SEC-05

Scope and handoff: Sprint 1 active-exchange guard is a test double; real exchange query and integration test required in Sprint 2.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-13 [NF-001] Seed script and Locust performance test

Owner: Manoj
Epic: Listings

Acceptance criteria
NF-001: The search API shall achieve p90 response time <=2 seconds with 50 concurrent users over a 1-minute run, ramping at 10 users/second, using 10,000 listings and about 2,000 books. Report errors, host resources and cold-start exclusions; do not claim success from an unrepresentative sample.

Tests: TC-PERF-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-14 [F-001 F-002 NF-003] UI shell, routing, Register and Login pages

Owner: Ravish
Epic: Auth

Acceptance criteria
F-001: The system shall register students using an allowed university email domain. Lowercase email; name 1-100 characters; password at least 8 characters with a letter and digit. Valid input returns 201; duplicate email 409; other domains 400; invalid fields 422. New users have the student role.

F-002: The system shall authenticate email and password and issue a 30-minute JWT. Valid credentials return 200 with token and expiresIn=1800. Unknown email and wrong password both return the same 401 INVALID_CREDENTIALS.

NF-003: The UI shall work at 360px width without horizontal scrolling. From the authenticated Browse page, entering the listing flow and submitting it, and entering a query and displaying results, shall each require <=5 clicks; typing and tabbing are not clicks. Inputs have labels and errors are readable.

Tests: TC-AUTH-01, TC-AUTH-02, TC-AUTH-03, TC-AUTH-04, TC-SEC-01, TC-SEC-02, TC-UX-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-15 [F-011] UI Browse and Search page

Owner: Ravish
Epic: Listings

Acceptance criteria
F-011: The system shall publicly search AVAILABLE, non-deleted listings by title/author q, ISBN and location with pagination. Defaults page=1,size=20; size above 100 or page below 1 returns 422. Unknown searches return an empty items list. Authenticated /listings/mine returns only the caller's non-deleted listings including unavailable ones.

Tests: TC-LST-03, TC-LST-04, TC-LST-08

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-16 [F-004 F-010 F-012 F-013] UI My Listings and Profile pages

Owner: Ravish
Epic: Listings

Acceptance criteria
F-004: The system shall allow an authenticated student to view and edit name, department and location. Saved changes appear in the next GET. Email, role, active and password_hash cannot be changed via this endpoint.

F-010: The system shall create a listing for its authenticated owner, reuse a book by normalized unique ISBN, and set status AVAILABLE. Require title 1-200, author 1-150, location 1-100 and condition NEW/GOOD/FAIR/POOR. ISBN is 10 or 13 digits after hyphen removal in this course baseline. Valid input returns 201; invalid fields 422.

F-012: The system shall allow the owner to partially update a listing, including AVAILABLE/UNAVAILABLE status. Non-owners receive 403; missing/deleted IDs 404. Reserved or on-loan listings cannot be changed to available or have their book changed.

F-013: The system shall soft-delete owner listings and return 204. Non-owners receive 403. A listing involved in an active exchange cannot be deleted (409 ACTIVE_EXCHANGE). Deleted listings are excluded from public and own-listing queries.

Tests: TC-LST-01, TC-LST-02, TC-LST-05, TC-LST-06, TC-LST-07, TC-PRF-01, TC-PRF-02, TC-SEC-04, TC-SEC-05

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S1-17 [NF-003] Demo video, RTM update and deviations

Owner: Ravish
Epic: DevOps

Acceptance criteria
NF-003: The UI shall work at 360px width without horizontal scrolling. From the authenticated Browse page, entering the listing flow and submitting it, and entering a query and displaying results, shall each require <=5 clicks; typing and tabbing are not clicks. Inputs have labels and errors are readable.

Tests: TC-UX-01

Scope and handoff: Record about one minute at deployed URL; keep demo/sprint1.mp4 under 100 MB; update only verified RTM results. No fabricated passing tests.

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-01 [F-020] Create borrow request

Owner: Manoj (proposed; confirm 2 November)
Epic: Requests & Matching

Acceptance criteria
F-020: The system shall let an authenticated student create an OPEN borrow request specifying ISBN or a nonempty title query and location. Invalid input returns 422; duplicate active requests by the same student and criteria return 409.

Tests: TC-REQ-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-02 [F-021] Cancel request

Owner: Manoj (proposed; confirm 2 November)
Epic: Requests & Matching

Acceptance criteria
F-021: The system shall allow only the borrower to cancel an OPEN or MATCHED request. Cancel linked pending matches and release any uncommitted reservation atomically. An accepted exchange must use its exchange cancellation transition; non-owner requests return 403.

Tests: TC-REQ-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-03 [F-022] Matching engine with scoring, locking and re-match

Owner: Manoj (proposed; confirm 2 November)
Epic: Requests & Matching

Acceptance criteria
F-022: The system shall rank available non-deleted listings from other active users using ISBN or title relevance, location and condition. Return at most five deterministic suggestions. Recompute after decline, cancellation or listing changes; never reserve one listing for two active exchanges.

Tests: TC-MAT-01, TC-MAT-02, TC-MAT-03

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-04 [F-023] In-app notifications

Owner: Abhiram (proposed; confirm 2 November)
Epic: Exchange

Acceptance criteria
F-023: The system shall create durable in-app notifications for new matches, partner decisions and exchange changes. Users can view and mark only their own notifications as read. Reprocessing the same event shall not duplicate notifications.

Tests: TC-NOT-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-05 [F-024] Accept and decline match

Owner: Manoj (proposed; confirm 2 November)
Epic: Requests & Matching

Acceptance criteria
F-024: The system shall allow each participant to accept or decline a proposed match. Only mutual acceptance creates an exchange and permits contact disclosure. A stale or conflicting decision returns 409 and cannot create a second active exchange.

Tests: TC-MAT-04, TC-SEC-07

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-06 [F-025] Exchange lifecycle and agreed due date

Owner: Abhiram (proposed; confirm 2 November)
Epic: Exchange

Acceptance criteria
F-025: The system shall record an agreed future due date for an ACCEPTED exchange and move it to ON_LOAN when the lender confirms handover. Either participant may cancel before handover; cancellation after handover is rejected. Transitions require participant authorization and retain history.

Tests: TC-EXC-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-07 [F-026] Confirm return

Owner: Abhiram (proposed; confirm 2 November)
Epic: Exchange

Acceptance criteria
F-026: The system shall record each participant's return confirmation. Only both confirmations move ON_LOAN to RETURNED and restore listing availability. Repeated confirmations are idempotent.

Tests: TC-EXC-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-08 [F-030] Exchange history

Owner: Abhiram (proposed; confirm 2 November)
Epic: Exchange

Acceptance criteria
F-030: The system shall return paginated past and current exchanges only to their participants, including book, dates, partner display name and state. Other students cannot read the exchange.

Tests: TC-HIS-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-09 [F-031] Ratings

Owner: Abhiram (proposed; confirm 2 November)
Epic: Exchange

Acceptance criteria
F-031: The system shall permit each participant to rate their partner once per RETURNED exchange using an integer 1-5. Reject self-rating, pre-return ratings and duplicates. Recompute the recipient average from accepted ratings.

Tests: TC-RAT-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-10 [F-040] Admin moderation and audit log

Owner: Nishkal (proposed; confirm 2 November)
Epic: Admin

Acceptance criteria
F-040: The system shall allow admins to deactivate abusive users and hide listings with a required reason, recording actor, target, action and time. Student access returns 403. Inactive users cannot authenticate or use existing tokens. Audit records are not editable through public APIs.

Tests: TC-ADM-01, TC-ADM-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-11 [SR-007] Contact privacy until mutual acceptance

Owner: Nishkal (proposed; confirm 2 November)
Epic: Admin

Acceptance criteria
SR-007: Email and other contact details shall remain hidden from other students until a specific match is mutually accepted. Only that exchange's participants may retrieve its contact data; cancelled exchanges lose contact access.

Tests: TC-SEC-07

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-12 [SR-003 NF-002] TLS verification and uptime report

Owner: Nishkal (proposed; confirm 2 November)
Epic: DevOps

Acceptance criteria
SR-003: Deployed browser/API traffic shall use HTTPS and valid certificates; HTTP redirects to HTTPS without transmitting credentials. Verify TLS 1.2 or later. Restrict CORS to the configured frontend and keep secrets out of the repository.

NF-002: The deployed demo shall target >=99% successful /health probes during 2-7 November, measured every five minutes. Count sleep and unexpected outages as failures; disclose planned maintenance and missing measurements. This short-window target is not a monthly SLA.

Tests: TC-OPS-01, TC-SEC-03

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-13 [NF-005] Matching performance benchmark

Owner: Nishkal (proposed; confirm 2 November)
Epic: Requests & Matching

Acceptance criteria
NF-005: The matching engine shall produce the top five candidates at p95 <=2 seconds for 1,000 open requests against 10,000 listings, measured across at least 100 evaluations with 10 concurrent callers on a documented test host. Correctness and race tests remain mandatory.

Tests: TC-PERF-02

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.

### S2-14 [ALL] Final documentation, deviations and demo video

Owner: Ravish (proposed; confirm 2 November)
Epic: DevOps

Acceptance criteria
F-001: The system shall register students using an allowed university email domain. Lowercase email; name 1-100 characters; password at least 8 characters with a letter and digit. Valid input returns 201; duplicate email 409; other domains 400; invalid fields 422. New users have the student role.

F-002: The system shall authenticate email and password and issue a 30-minute JWT. Valid credentials return 200 with token and expiresIn=1800. Unknown email and wrong password both return the same 401 INVALID_CREDENTIALS.

F-003: The system shall invalidate all existing tokens for the current user by atomically incrementing token_version on logout (204). Expired, tampered or version-mismatched tokens shall return 401 on protected endpoints.

F-004: The system shall allow an authenticated student to view and edit name, department and location. Saved changes appear in the next GET. Email, role, active and password_hash cannot be changed via this endpoint.

F-010: The system shall create a listing for its authenticated owner, reuse a book by normalized unique ISBN, and set status AVAILABLE. Require title 1-200, author 1-150, location 1-100 and condition NEW/GOOD/FAIR/POOR. ISBN is 10 or 13 digits after hyphen removal in this course baseline. Valid input returns 201; invalid fields 422.

F-011: The system shall publicly search AVAILABLE, non-deleted listings by title/author q, ISBN and location with pagination. Defaults page=1,size=20; size above 100 or page below 1 returns 422. Unknown searches return an empty items list. Authenticated /listings/mine returns only the caller's non-deleted listings including unavailable ones.

F-012: The system shall allow the owner to partially update a listing, including AVAILABLE/UNAVAILABLE status. Non-owners receive 403; missing/deleted IDs 404. Reserved or on-loan listings cannot be changed to available or have their book changed.

F-013: The system shall soft-delete owner listings and return 204. Non-owners receive 403. A listing involved in an active exchange cannot be deleted (409 ACTIVE_EXCHANGE). Deleted listings are excluded from public and own-listing queries.

F-020: The system shall let an authenticated student create an OPEN borrow request specifying ISBN or a nonempty title query and location. Invalid input returns 422; duplicate active requests by the same student and criteria return 409.

F-021: The system shall allow only the borrower to cancel an OPEN or MATCHED request. Cancel linked pending matches and release any uncommitted reservation atomically. An accepted exchange must use its exchange cancellation transition; non-owner requests return 403.

F-022: The system shall rank available non-deleted listings from other active users using ISBN or title relevance, location and condition. Return at most five deterministic suggestions. Recompute after decline, cancellation or listing changes; never reserve one listing for two active exchanges.

F-023: The system shall create durable in-app notifications for new matches, partner decisions and exchange changes. Users can view and mark only their own notifications as read. Reprocessing the same event shall not duplicate notifications.

F-024: The system shall allow each participant to accept or decline a proposed match. Only mutual acceptance creates an exchange and permits contact disclosure. A stale or conflicting decision returns 409 and cannot create a second active exchange.

F-025: The system shall record an agreed future due date for an ACCEPTED exchange and move it to ON_LOAN when the lender confirms handover. Either participant may cancel before handover; cancellation after handover is rejected. Transitions require participant authorization and retain history.

F-026: The system shall record each participant's return confirmation. Only both confirmations move ON_LOAN to RETURNED and restore listing availability. Repeated confirmations are idempotent.

F-030: The system shall return paginated past and current exchanges only to their participants, including book, dates, partner display name and state. Other students cannot read the exchange.

F-031: The system shall permit each participant to rate their partner once per RETURNED exchange using an integer 1-5. Reject self-rating, pre-return ratings and duplicates. Recompute the recipient average from accepted ratings.

F-040: The system shall allow admins to deactivate abusive users and hide listings with a required reason, recording actor, target, action and time. Student access returns 403. Inactive users cannot authenticate or use existing tokens. Audit records are not editable through public APIs.

NF-001: The search API shall achieve p90 response time <=2 seconds with 50 concurrent users over a 1-minute run, ramping at 10 users/second, using 10,000 listings and about 2,000 books. Report errors, host resources and cold-start exclusions; do not claim success from an unrepresentative sample.

NF-002: The deployed demo shall target >=99% successful /health probes during 2-7 November, measured every five minutes. Count sleep and unexpected outages as failures; disclose planned maintenance and missing measurements. This short-window target is not a monthly SLA.

NF-003: The UI shall work at 360px width without horizontal scrolling. From the authenticated Browse page, entering the listing flow and submitting it, and entering a query and displaying results, shall each require <=5 clicks; typing and tabbing are not clicks. Inputs have labels and errors are readable.

NF-004: Each main-branch PR shall run lint, backend tests with >=70% application coverage, frontend production build and Docker build. Required checks and one independent approval gate merging. Auth coverage shall exceed 85% by the end of Sprint 1. Deployment runs only after successful main builds.

NF-005: The matching engine shall produce the top five candidates at p95 <=2 seconds for 1,000 open requests against 10,000 listings, measured across at least 100 evaluations with 10 concurrent callers on a documented test host. Correctness and race tests remain mandatory.

NF-006: A fresh checkout with documented environment values shall start backend, frontend and Postgres using docker compose up --build, apply migrations and pass registration/login/listing smoke tests without manual database edits.

SR-001: The system shall store only salted bcrypt hashes and never return or log passwords or hashes. Reject passwords over 72 UTF-8 bytes to avoid bcrypt truncation. Public response schemas exclude secrets.

SR-002: Protected routes shall verify JWT signature using an explicit HS256 allowlist, exp, subject, current active user and token_version. Tokens expire after 30 minutes; missing/invalid/expired tokens return 401. JWT_SECRET is supplied outside source control.

SR-003: Deployed browser/API traffic shall use HTTPS and valid certificates; HTTP redirects to HTTPS without transmitting credentials. Verify TLS 1.2 or later. Restrict CORS to the configured frontend and keep secrets out of the repository.

SR-004: The system shall validate request fields server-side and use ORM or bound SQL parameters. SQL-looking input must not alter query structure or expose unrelated rows; HTML content is rendered as text.

SR-005: Every mutation shall enforce ownership or an explicit admin role server-side. Reject non-owner listing edits/deletes with 403 and profile privilege escalation with 422. Return only public fields in listing views.

SR-006: After five failed logins for the normalized email/client IP pair in 15 minutes, the next attempt returns 429 and Retry-After, including a correct password. Successful login before the limit clears failures. Expired failures are removed.

SR-007: Email and other contact details shall remain hidden from other students until a specific match is mutually accepted. Only that exchange's participants may retrieve its contact data; cancelled exchanges lose contact access.

Tests: TC-ADM-01, TC-ADM-02, TC-AUTH-01, TC-AUTH-02, TC-AUTH-03, TC-AUTH-04, TC-AUTH-05, TC-AUTH-06, TC-CI-01, TC-EXC-01, TC-EXC-02, TC-HIS-01, TC-LST-01, TC-LST-02, TC-LST-03, TC-LST-04, TC-LST-05, TC-LST-06, TC-LST-07, TC-LST-08, TC-MAT-01, TC-MAT-02, TC-MAT-03, TC-MAT-04, TC-NOT-01, TC-OPS-01, TC-PERF-01, TC-PERF-02, TC-PORT-01, TC-PRF-01, TC-PRF-02, TC-RAT-01, TC-REQ-01, TC-REQ-02, TC-SEC-01, TC-SEC-02, TC-SEC-03, TC-SEC-04, TC-SEC-05, TC-SEC-06, TC-SEC-07, TC-UX-01

Definition of done: reviewed PR with Jira key merged; applicable tests pass in CI; no secrets; evidence linked; deviations recorded; Jira updated that day.
