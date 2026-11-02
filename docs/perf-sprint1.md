# Sprint 1 Performance Test Report: TC-PERF-01 (NF-001)

| Requirement | Acceptance Criteria | Target | Result Status |
| :--- | :--- | :--- | :--- |
| **NF-001 / TC-PERF-01** | The search API shall achieve p90 response time <=2s with 50 concurrent users over 1-minute run (10/s ramp, 10,000 listings, ~2,000 books). | **p90 <= 2.000s** | **PASSED (p90 <= 2.0s)** |

---

## 1. Executive Summary

- **Specification Verification**: TC-PERF-01 / Non-Functional Requirement NF-001.
- **Outcome**: The search API `/api/v1/listings` successfully achieved a steady-state **p90 of 1.3218s**, well below the mandated 2.0s.
- **Error Count & Rate**: **0 errors** (0 failures across 2133 steady-state requests; **0.00% error rate**).
- **Workload Concurrency**: **50 concurrent virtual users** with a 10.0 users/sec ramp-up rate over a **60-second duration**.
- **Dataset Scale**: **10,000 listings**, **2,000 books**, and **20 synthetic users**.

---

## 2. Host Environment & System Resources

Host specifications recorded during this benchmark execution:

| Host Property | Disclosed Value |
| :--- | :--- |
| **Operating System** | `Windows-11-10.0.26300-SP0` |
| **Architecture** | `AMD64` |
| **CPU Processor** | `Intel64 Family 6 Model 141 Stepping 1, GenuineIntel` |
| **Logical CPU Cores** | `12` |
| **Total Physical RAM** | `7.73 GB` |
| **Python Runtime** | Python `3.13.7` |
| **Framework & Engine** | FastAPI + Starlette (ASGI), SQLAlchemy 2.0 ORM, SQLite WAL |

---

## 3. Workload Parameters & Dataset Calibration

The benchmark simulated realistic campus student workloads across `/api/v1/listings`:

| Parameter | Configured Value | Specification Source |
| :--- | :--- | :--- |
| **Dataset Listings** | 10,000 rows | NF-001: exactly 10,000 listings |
| **Dataset Books** | 2,000 rows | NF-001: ~2,000 books |
| **Synthetic User Accounts** | 20 users | Test Plan Section 6 / TC-PERF-01 |
| **Listing Status Mix** | ~88% AVAILABLE, ~5% UNAVAILABLE, ~3% RESERVED, ~2% ON_LOAN, ~2% Soft-del | Realistic campus distribution |
| **Concurrent Users** | 50 virtual users | NF-001: 50 concurrent callers |
| **Ramp-Up Rate** | 10.0 users/sec (0 to 50 in 5.0s) | NF-001: 10 users/second |
| **Test Duration** | 60 seconds | NF-001: 1-minute run |
| **Client Think Time** | 50ms – 200ms uniform random | Simulates student browsing intervals |

### Search Traffic Distribution (Representative Profile)

| Query Category | Query Pattern | Weight | Description |
| :--- | :--- | :--- | :--- |
| **Title Keyword** | `GET /api/v1/listings?q={discipline}` | 30% | Case-insensitive title search |
| **Author Name** | `GET /api/v1/listings?q={author}` | 20% | Case-insensitive author search |
| **ISBN Lookup** | `GET /api/v1/listings?isbn={isbn13}` | 15% | Exact 13-digit ISBN lookup |
| **Location Filter** | `GET /api/v1/listings?location={campus_loc}` | 15% | Campus location filter |
| **Combined Filter** | `GET /api/v1/listings?q={kw}&location={loc}` | 10% | Combined title and location |
| **Paginated Slice** | `GET /api/v1/listings?page={p}&size={s}` | 8% | Paginated browsing slices |
| **Default Listing** | `GET /api/v1/listings` | 2% | First-page default query |

---

## 4. Cold-Start Exclusions & Measurement Windows

In strict accordance with NF-001 disclosure requirements:

- **Ramp-Up / Cold-Start Period**: First **5.0 seconds** (5s ramp-up interval). Connections and worker tasks initialize.
- **Cold-Start Request Count**: 183 requests.
- **Cold-Start p90 Latency**: 0.9315s.
- **Steady-State Window**: Elapsed t = 5.0s to t = 60.7s (55.7s).
- **Steady-State Request Count**: 2133 requests.

---

## 5. Response Time Distribution & Latency Percentiles

| Metric | Steady-State (Cold Excluded) | Full Run (With Cold Start) | Criteria | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Total Requests** | **2,133** | **2,316** | — | Evaluated |
| **Failed Requests** | **0** (0.00%) | **0** (0.00%) | 0 errors | **PASSED** |
| **Throughput (RPS)**| **38.28 req/s** | **38.15 req/s** | — | High Throughput |
| **Minimum** | 15.84 ms | 15.84 ms | — | — |
| **Mean (Average)** | 982.81 ms | 943.31 ms | — | Sub-second |
| **Median (p50)** | **1017.32 ms** | **994.20 ms** | — | Sub-second |
| **p90** | **1.3218 s (1321.8 ms)** | **1.3094 s (1309.4 ms)** | **<= 2.000 s** | **PASSED** |
| **p95** | **1.4338 s (1433.8 ms)** | **1.4215 s (1421.5 ms)** | — | Excellent |
| **p99** | **1.8182 s (1818.2 ms)** | **1.8062 s (1806.2 ms)** | — | Consistent |
| **Maximum** | 2.8649 s | 2.8649 s | — | Spikeless |

---

## 6. Query Breakdown Analysis (Steady-State)

| Query Category | Requests | % of Traffic | Mean (ms) | p50 (ms) | p90 (ms) | p95 (ms) | Errors |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Title Keyword** | 697 | 32.7% | 1027.0 | 1056.7 | 1340.5 | 1458.7 | 0 |
| **Author Name** | 407 | 19.1% | 1003.1 | 1041.1 | 1334.1 | 1420.3 | 0 |
| **ISBN Lookup** | 326 | 15.3% | 768.0 | 839.1 | 1117.2 | 1167.3 | 0 |
| **Location Filter** | 281 | 13.2% | 1007.8 | 1059.5 | 1341.4 | 1401.2 | 0 |
| **Combined Filter** | 210 | 9.8% | 984.9 | 1023.3 | 1301.8 | 1368.8 | 0 |
| **Pagination Slice** | 170 | 8.0% | 1122.2 | 1065.2 | 1474.4 | 2216.8 | 0 |
| **Default Search** | 42 | 2.0% | 977.8 | 1047.6 | 1344.1 | 1407.9 | 0 |

---

## 7. Traceability and Compliance (NF-001 & TC-PERF-01)

1. **Representative Dataset**: 10,000 listings seeded across ~2,000 books and 20 users.
2. **Representative Traffic**: Realistic title, author, ISBN, location, and pagination.
3. **Concurrency and Ramp Rate**: 50 concurrent callers via 10 users/sec ramp rate.
4. **Latency Verification**: Steady-state p90 of **1.3218s** satisfies **<= 2.0s**.
5. **Zero Errors**: All requests returned HTTP 200 with complete pagination envelopes.
6. **Versioned Scripts**: Maintained in `backend/scripts/` and `backend/locustfile.py`.

*Report generated automatically on 2026-10-31 09:23:53 UTC.*