# Code Coverage Report (statement coverage)

| Item | Value |
| :--- | :--- |
| Generated | 05 Nov 2026 21:51 |
| Commit | `ba0e726 (+ uncommitted changes)` |
| Python | 3.13.7 on Windows |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Statements | Missed | Statement coverage | CI gate |
| ---: | ---: | ---: | :--- |
| 1371 | 72 | **94.7%** | >= 70% (met) |

The CI gate (`--cov-fail-under=70`) uses the combined statement and branch figure, currently 92.7%.

## Coverage by file

| File | Statements | Missed | Coverage |
| :--- | ---: | ---: | ---: |
| `app/config.py` | 27 | 0 | 100% |
| `app/database.py` | 15 | 0 | 100% |
| `app/login_rate_limit.py` | 42 | 0 | 100% |
| `app/main.py` | 22 | 0 | 100% |
| `app/models.py` | 134 | 0 | 100% |
| `app/routers/admin.py` | 38 | 3 | 92% |
| `app/routers/auth.py` | 174 | 13 | 93% |
| `app/routers/exchanges.py` | 302 | 9 | 97% |
| `app/routers/listings.py` | 203 | 14 | 93% |
| `app/routers/matches.py` | 44 | 0 | 100% |
| `app/routers/notifications.py` | 37 | 0 | 100% |
| `app/routers/requests.py` | 121 | 14 | 88% |
| `app/services/matching.py` | 196 | 17 | 91% |
| `app/services/notifications.py` | 16 | 2 | 88% |
