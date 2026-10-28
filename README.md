# Book Exchange Platform

A peer-to-peer student book lending and borrowing platform with authenticated listings, ranked requests and coordinated exchanges on a relational database.

## Submission documents

| Deliverable | PDF | Editable source |
| --- | --- | --- |
| Software Requirements Specification | [SRS](documents/SRS.pdf) | [SRS source](documents/SRS.md) |
| Software Architecture and Design | [SAD](documents/SAD.pdf) | [SAD source](documents/SAD.md) |
| Software Test Plan | [Test Plan](documents/Test_Plan.pdf) | [Test Plan source](documents/Test_Plan.md) |

The documents form the initial project baseline. Implementation, CI runs and test execution are pending; no test is represented as passed.

## Team

| Member | Responsibility |
| --- | --- |
| Nishkal | Repository, Jira, DevOps, CI/CD and deployment |
| Abhiram | Authentication and profile |
| Manoj | Listings and search |
| Ravish | UI, documentation and demonstration |

These roles reflect the confirmed swap and override the names in the supplied task-plan PDF.

## Schedule

- Deliverables: 27 October 2026, before Sprint 1 starts.
- Sprint 1: 27-31 October 2026; aim to merge by 30 October, 18:00 IST.
- Sprint 2: 2-7 November 2026.
- Presentations: from 9 November 2026.

[Jira backlog](https://nishkalmr321.atlassian.net/jira/software/projects/BEP/boards/3/backlog) · [Sprint checklist](documents/SPRINT-1-CHECKLIST.md) · [Prepared backlog](documents/JIRA-BACKLOG.md) · [Current setup status](documents/TODAY.md)

## Development workflow

Use branches `BEP-<issue-number>-short-name`. Include the real Jira key in the PR title. Require one independent approval and passing required CI; do not approve your own work. Move work through To Do → In Progress → In Review → Done and retain test evidence.

## Planned setup

The 28 October scaffold will provide FastAPI, React/Vite, PostgreSQL and Docker Compose. The intended startup is `docker compose up --build` after configuring a local `.env` from `.env.example`. This command is not yet runnable in this documentation-only baseline. Do not commit credentials or claim a deployment URL until it is verified.

