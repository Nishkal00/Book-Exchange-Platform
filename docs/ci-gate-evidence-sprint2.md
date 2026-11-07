# TC-CI-01 CI Gate Evidence (NF-004 / DevOps)

| Item | Value |
|---|---|
| Test case | TC-CI-01 |
| Date | 7 November 2026 |
| Method | A throwaway branch `BEP-ci-gate-demo` added one deliberately failing test (`backend/tests/test_ci_gate_demo.py`, `assert 1 == 2`), was pushed and opened as pull request #76 against `main`. A second commit then removed the test and was pushed to the same PR. |
| Result | **Pass** for the failing-gate and recovery checks. The deploy check is covered by the skipped deploy job (section 4). |
| Disposition | PR #76 is a demonstration only and is closed without merging. Nothing from it reached `main`. |

## 1. Failing change is caught

| Check | Result | Screenshot |
|---|---|---|
| `CI / backend (lint, tests, migrations)` | Failed (56 s). The log shows `FAILED tests/test_ci_gate_demo.py::test_ci_gate_demo_failure - assert 1 == 2`, `1 failed, 177 passed`, then `Process completed with exit code 1` | `04-pr76-failed-job-log.png` |
| `CI / frontend (build)` | Passed (14 s) | `03-pr76-failing-check-red.png` |
| `CI / docker (build images)` | Skipped, because it depends on backend and frontend | `03-pr76-failing-check-red.png` |
| `CI / deploy (Render, main only)` | Skipped on a pull request | `03-pr76-failing-check-red.png` |
| Coverage gate | Total coverage 92.72%; "Required test coverage of 70% reached", so only the test failure broke the build | `04-pr76-failed-job-log.png` |

The backend and docker checks carry the "Required" badge, so the failing required check keeps the PR from merging. The merge box visible in screenshot 03 is cut off at the bottom of the page; it shows the failing required check and the open review requirement. The review requirement is shown blocking a merge in section 3.

## 2. Fix restores a green gate

After the restore commit (the deliberate test removed) was pushed to the same PR, the checks re-ran:

| Check | Result | Screenshot |
|---|---|---|
| backend | Passed (49 s); lint, unit tests with coverage, and migrations steps all green | `06-pr76-after-fix-backend-steps-green.png` |
| docker | Passed (43 s) | `05-pr76-after-fix-all-green.png` |
| frontend | Passed (14 s) | `05-pr76-after-fix-all-green.png` |
| deploy | Skipped | `05-pr76-after-fix-all-green.png` |

The PR then showed "All checks have passed" with 2 commits (the failing commit and the restore).

## 3. Review gate (PR #75)

On an earlier pull request (#75) with all checks green, GitHub still showed "Merging is blocked: At least 1 approving review is required", and the Merge button was disabled. After one approval the merge button became available.

| Situation | Screenshot |
|---|---|
| Checks green, no approval: merge blocked | `01-pr75-blocked-no-review.png` |
| Checks green, approved: merge enabled | `02-pr75-approved-merge-enabled.png` |

## 4. Pull requests do not deploy

The `deploy (Render, main only)` job is skipped on pull requests in screenshots 01, 02, 03, 05, and PR #76 shows "This branch has not been deployed". The deploy job runs only after a merge to `main`. This report does not show a real deployment from a green `main`.

## 5. Limitations

1. The screenshot of the failing PR cuts off before the merge box, so the blocked-merge text in screenshots 01 and 03 refers to the review requirement. The failing check is marked Required and red.
2. The Auth coverage threshold (above 85%) was not shown in this run.
3. The check ran once, on this repository's current branch protection rules.

## 6. Conclusion

A failing test turned the required backend check red, the downstream docker job did not run, the review requirement blocked merging, deploy did not run on the PR, and removing the failing test returned all required checks to green. TC-CI-01 can be recorded as Pass with the limitations above.
