# Development Freeze (Sprint 2)

| Item | Value |
| :--- | :--- |
| Sprint | BEP Sprint 2 (2 Nov to 7 Nov 2026) |
| Freeze time | **Saturday 7 Nov 2026, 11:59 PM IST** |
| Scope of the freeze | No new features or behaviour changes after this time. |

## What is allowed after the freeze

- Evidence and documentation only: test reports in `docs/`, the RTM and Test Plan results, the
  deviations log, the uptime table for NF-002 (BEP-35) and the final demo video.
- Fixes for a defect found during final verification, only with a Jira card, a reviewed PR and the
  deviation recorded in `documents/DEVIATIONS.md`.

## What happens at the freeze

1. Every Sprint 2 card is either Done (reviewed PR merged) or has a comment explaining why not.
2. Requirements that are not fully delivered are listed in `documents/DEVIATIONS.md`.
3. The repository owner tags the final commit (for example `git tag v1.0-sprint2` and
   `git push origin v1.0-sprint2`), and the commit hash is recorded in the RTM.
4. The test reports in `docs/` are regenerated from that commit
   (`python backend/scripts/generate_test_reports.py`).

## Contribution tracking

`.mailmap` maps each person's different commit names to one identity, so `git shortlog -sne`
shows one line per team member.
