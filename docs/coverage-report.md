# Code Coverage Report (statement coverage)

| Item | Value |
| :--- | :--- |
| Generated | 04 Nov 2026 14:50 |
| Commit | `77b5d7f (+ uncommitted changes)` |
| Python | 3.13.17 on Linux |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Statements | Missed | Statement coverage | CI gate |
| ---: | ---: | ---: | :--- |
| 1218 | 76 | **93.8%** | >= 70% (met) |

The CI gate (`--cov-fail-under=70`) uses the combined statement and branch figure, currently 91.5%.

## Coverage by file

| File | Statements | Missed | Coverage |
| :--- | ---: | ---: | ---: |
| `app/config.py` | 27 | 0 | 100% |
| `app/database.py` | 15 | 0 | 100% |
| `app/login_rate_limit.py` | 42 | 0 | 100% |
| `app/main.py` | 20 | 0 | 100% |
| `app/models.py` | 116 | 0 | 100% |
| `app/routers/auth.py` | 170 | 18 | 89% |
| `app/routers/exchanges.py` | 227 | 2 | 99% |
| `app/routers/listings.py` | 203 | 14 | 93% |
| `app/routers/matches.py` | 44 | 0 | 100% |
| `app/routers/notifications.py` | 37 | 0 | 100% |
| `app/routers/requests.py` | 121 | 14 | 88% |
| `app/services/matching.py` | 180 | 26 | 86% |
| `app/services/notifications.py` | 16 | 2 | 88% |
