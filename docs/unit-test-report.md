# Unit Test Report (backend)

| Item | Value |
| :--- | :--- |
| Generated | 06 Nov 2026 18:01 |
| Commit | `b3b9eec` |
| Python | 3.13.17 on Linux |
| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |

## Summary

| Total | Passed | Failed | Skipped | Duration |
| ---: | ---: | ---: | ---: | ---: |
| 177 | 177 | 0 | 0 | 29.9 s |

Database: in-memory SQLite for unit tests. PostgreSQL-only behaviour is exercised by the
CI migration step against a real PostgreSQL service.

## Results by test file

| Test file | Tests | Passed | Failed | Skipped |
| :--- | ---: | ---: | ---: | ---: |
| `tests/test_admin.py` | 13 | 13 | 0 | 0 |
| `tests/test_auth_login.py` | 7 | 7 | 0 | 0 |
| `tests/test_auth_logout.py` | 8 | 8 | 0 | 0 |
| `tests/test_auth_register.py` | 3 | 3 | 0 | 0 |
| `tests/test_config.py` | 2 | 2 | 0 | 0 |
| `tests/test_config_database_url.py` | 3 | 3 | 0 | 0 |
| `tests/test_exchange_return.py` | 9 | 9 | 0 | 0 |
| `tests/test_exchanges.py` | 23 | 23 | 0 | 0 |
| `tests/test_health.py` | 2 | 2 | 0 | 0 |
| `tests/test_listings.py` | 14 | 14 | 0 | 0 |
| `tests/test_login_rate_limit.py` | 5 | 5 | 0 | 0 |
| `tests/test_match_decision.py` | 11 | 11 | 0 | 0 |
| `tests/test_match_list.py` | 4 | 4 | 0 | 0 |
| `tests/test_matching.py` | 12 | 12 | 0 | 0 |
| `tests/test_models.py` | 8 | 8 | 0 | 0 |
| `tests/test_notifications.py` | 7 | 7 | 0 | 0 |
| `tests/test_perf_seed.py` | 7 | 7 | 0 | 0 |
| `tests/test_profile.py` | 7 | 7 | 0 | 0 |
| `tests/test_ratings.py` | 16 | 16 | 0 | 0 |
| `tests/test_requests.py` | 8 | 8 | 0 | 0 |
| `tests/test_security_evidence.py` | 8 | 8 | 0 | 0 |

## Failures

None.
