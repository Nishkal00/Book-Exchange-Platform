# Unit Test Report (backend)

| Item | Value |
| :--- | :--- |
| Generated | 04 Nov 2026 14:50 |
| Commit | `77b5d7f (+ uncommitted changes)` |
| Python | 3.13.17 on Linux |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Total | Passed | Failed | Skipped | Duration |
| ---: | ---: | ---: | ---: | ---: |
| 133 | 133 | 0 | 0 | 16.9 s |

Database: in-memory SQLite for unit tests. PostgreSQL-only behaviour is exercised by the
CI migration step against a real PostgreSQL service.

## Results by test file

| Test file | Tests | Passed | Failed | Skipped |
| :--- | ---: | ---: | ---: | ---: |
| `tests/test_auth_login.py` | 7 | 7 | 0 | 0 |
| `tests/test_auth_logout.py` | 8 | 8 | 0 | 0 |
| `tests/test_auth_register.py` | 3 | 3 | 0 | 0 |
| `tests/test_config.py` | 2 | 2 | 0 | 0 |
| `tests/test_config_database_url.py` | 3 | 3 | 0 | 0 |
| `tests/test_exchange_return.py` | 9 | 9 | 0 | 0 |
| `tests/test_exchanges.py` | 19 | 19 | 0 | 0 |
| `tests/test_health.py` | 2 | 2 | 0 | 0 |
| `tests/test_listings.py` | 14 | 14 | 0 | 0 |
| `tests/test_login_rate_limit.py` | 5 | 5 | 0 | 0 |
| `tests/test_match_decision.py` | 11 | 11 | 0 | 0 |
| `tests/test_match_list.py` | 4 | 4 | 0 | 0 |
| `tests/test_matching.py` | 12 | 12 | 0 | 0 |
| `tests/test_models.py` | 8 | 8 | 0 | 0 |
| `tests/test_notifications.py` | 7 | 7 | 0 | 0 |
| `tests/test_perf_seed.py` | 4 | 4 | 0 | 0 |
| `tests/test_profile.py` | 7 | 7 | 0 | 0 |
| `tests/test_requests.py` | 8 | 8 | 0 | 0 |

## Failures

None.
