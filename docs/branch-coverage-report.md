# Branch Coverage Report

| Item | Value |
| :--- | :--- |
| Generated | 04 Nov 2026 14:50 |
| Commit | `77b5d7f (+ uncommitted changes)` |
| Python | 3.13.17 on Linux |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Branches | Covered | Partially or not covered | Branch coverage |
| ---: | ---: | ---: | ---: |
| 280 | 229 | 51 | **81.8%** |

Branch coverage is switched on with `branch = true` in `backend/pyproject.toml`.

## Branch coverage by file

| File | Branches | Covered | Missed | Coverage |
| :--- | ---: | ---: | ---: | ---: |
| `app/config.py` | 4 | 4 | 0 | 100% |
| `app/login_rate_limit.py` | 10 | 10 | 0 | 100% |
| `app/routers/auth.py` | 40 | 31 | 9 | 78% |
| `app/routers/exchanges.py` | 40 | 38 | 2 | 95% |
| `app/routers/listings.py` | 58 | 48 | 10 | 83% |
| `app/routers/matches.py` | 2 | 2 | 0 | 100% |
| `app/routers/notifications.py` | 4 | 3 | 1 | 75% |
| `app/routers/requests.py` | 38 | 26 | 12 | 68% |
| `app/services/matching.py` | 78 | 64 | 14 | 82% |
| `app/services/notifications.py` | 6 | 3 | 3 | 50% |
