# Branch Coverage Report

| Item | Value |
| :--- | :--- |
| Generated | 05 Nov 2026 21:51 |
| Commit | `ba0e726 (+ uncommitted changes)` |
| Python | 3.13.7 on Windows |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Branches | Covered | Partially or not covered | Branch coverage |
| ---: | ---: | ---: | ---: |
| 310 | 260 | 50 | **83.9%** |

Branch coverage is switched on with `branch = true` in `backend/pyproject.toml`.

## Branch coverage by file

| File | Branches | Covered | Missed | Coverage |
| :--- | ---: | ---: | ---: | ---: |
| `app/config.py` | 4 | 4 | 0 | 100% |
| `app/login_rate_limit.py` | 10 | 10 | 0 | 100% |
| `app/routers/admin.py` | 8 | 5 | 3 | 62% |
| `app/routers/auth.py` | 42 | 36 | 6 | 86% |
| `app/routers/exchanges.py` | 52 | 47 | 5 | 90% |
| `app/routers/listings.py` | 58 | 48 | 10 | 83% |
| `app/routers/matches.py` | 2 | 2 | 0 | 100% |
| `app/routers/notifications.py` | 4 | 3 | 1 | 75% |
| `app/routers/requests.py` | 38 | 26 | 12 | 68% |
| `app/services/matching.py` | 86 | 76 | 10 | 88% |
| `app/services/notifications.py` | 6 | 3 | 3 | 50% |
