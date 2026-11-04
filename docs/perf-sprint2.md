# Sprint 2 Performance Test Report: TC-PERF-02 (NF-005)

| Requirement | Acceptance Criteria | Target | Result Status |
| :--- | :--- | :--- | :--- |
| **NF-005 / TC-PERF-02** | The matching engine shall produce the top five candidates at p95 <=2s for 1,000 open requests against 10,000 listings, measured across at least 100 evaluations with 10 concurrent callers. | **p95 <= 2.000s** | **PASSED (p95 <= 2.0s)** |

---

## 1. Executive Summary

- **Specification Verification**: TC-PERF-02 / Non-Functional Requirement NF-005.
- **Outcome**: The matching engine `/api/v1/requests/{id}/matches` successfully achieved a steady-state **p95 of 1.3594s**, comfortably under the mandated 2.0s threshold.
- **Error Count & Rate**: **0 errors** (0 failures across 100 steady-state evaluations; **0.00% error rate**).
- **Workload Concurrency**: **10 concurrent virtual callers** executing **100 evaluations**.
- **Dataset Scale**: **1,000 open requests**, **10,000 listings**, **2,000 books**, and **20 synthetic users**.
- **Candidate Output Constraint**: Every evaluation returned at most 5 candidates (observed range: 0 to 5, mean: 4.1).

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

The benchmark simulated realistic matching evaluations under the mandated test conditions:

| Parameter | Configured Value | Specification Source |
| :--- | :--- | :--- |
| **Open Borrow Requests** | 1,000 requests | NF-005: 1,000 open requests |
| **Dataset Listings** | 10,000 listings | NF-005: 10,000 listings |
| **Dataset Books** | 2,000 books | NF-005: ~2,000 books |
| **Synthetic User Accounts** | 20 users | Test Plan Section 6 / TC-PERF-02 |
| **Concurrent Callers** | 10 concurrent callers | NF-005: 10 concurrent callers |
| **Evaluations Measured** | 100 evaluations | NF-005: >=100 evaluations |
| **Warmup Evaluations** | 10 evaluations | Cold-start exclusion |

---

## 4. Cold-Start Exclusions & Measurement Windows

In strict accordance with NF-005 disclosure guidelines:

- **Cold-Start Phase**: Initial 10 evaluations reserved for engine and connection initialization.
- **Cold-Start p95 Latency**: 0.4832s.
- **Steady-State Window**: 100 evaluations executed across 4.03 seconds.
- **Steady-State Throughput**: 24.83 evaluations/sec.

---

## 5. Response Time Distribution & Latency Percentiles

| Metric | Steady-State (Cold Excluded) | Full Run (With Warmup) | Criteria | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Total Evaluations** | **100** | **110** | >= 100 evals | **PASSED** |
| **Failed Evaluations** | **0** (0.00%) | **0** (0.00%) | 0 fatal errors | **PASSED** |
| **Throughput (EPS)**| **24.83 eval/s** | **24.29 eval/s** | — | High Throughput |
| **Minimum** | 18.87 ms | 18.87 ms | — | — |
| **Mean (Average)** | 372.49 ms | 363.10 ms | — | Sub-second |
| **Median (p50)** | **81.60 ms** | **96.78 ms** | — | Highly responsive |
| **p90** | **1202.30 ms** | **1194.95 ms** | — | Consistent |
| **p95** | **1.3594 s (1359.4 ms)** | **1.3572 s** | **<= 2.000 s** | **PASSED (p95 <= 2.0s)** |
| **p99** | **1.6360 s (1636.0 ms)** | **1.6257 s** | — | Within bound |
| **Maximum** | 1.8680 s | 1.8680 s | — | Stable |

---

## 6. Request Breakdown Analysis (Steady-State)

| Query Type | Evaluations | % Share | Mean (ms) | p50 (ms) | p90 (ms) | p95 (ms) | Errors |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ISBN Lookup** | 68 | 68.0% | 69.9 | 60.4 | 113.9 | 138.6 | 0 |
| **Title Query** | 32 | 32.0% | 1015.4 | 947.5 | 1419.4 | 1584.9 | 0 |

---

## 7. Candidate Correctness & Invariant Verification

1. **Capped Output**: Across all evaluations, no result set exceeded the mandated upper bound of 5 candidate suggestions.
2. **Deterministic Tie-Breaking**: Candidates were sorted deterministically by descending score, newest listing creation time, and listing ID tie-break.
3. **Exclusion Invariants**: Confirmed 0 soft-deleted listings, 0 UNAVAILABLE listings, and 0 borrower self-listings present in candidate responses.
4. **Race & Concurrency Test**: Verified concurrent decisions on overlapping candidate listings atomically reserve listings and prevent double active exchanges (TC-MAT-04 / TC-SEC-07).

---

## 8. Compliance Statement

**Requirement NF-005 (TC-PERF-02) is verified as ACCEPTED**. The matching engine demonstrated a steady-state p95 response time of **1.3594s** under 10 concurrent virtual callers across a seeded dataset of 1,000 open borrow requests and 10,000 listings, with zero fatal errors and strict adherence to deterministic top-five candidate correctness.
