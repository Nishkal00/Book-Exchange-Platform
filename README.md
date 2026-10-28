# Book Exchange Platform

A peer-to-peer student book lending and borrowing platform with authenticated listings, ranked requests and coordinated exchanges on a relational database.

## Submission documents

| Deliverable | PDF |
| --- | --- |
| Software Requirements Specification | [SRS](documents/SRS.pdf) |
| Software Architecture and Design | [SAD](documents/SAD.pdf) |
| Software Test Plan | [Test Plan](documents/Test_Plan.pdf) |

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

[Jira backlog](https://nishkalmr321.atlassian.net/jira/software/projects/BEP/boards/3/backlog)

## Development workflow

Use branches `BEP-<issue-number>-short-name`. Include the real Jira key in the PR title. Require one independent approval and passing required CI; do not approve your own work. Move work through To Do → In Progress → In Review → Done and retain test evidence.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000 (health check: `/health`, interactive docs: `/docs`)
- The backend applies database migrations on start.

Backend development without Docker (Python 3.11, a local PostgreSQL 15 with `pg_trgm`):

```bash
cd backend
pip install -r requirements-dev.txt
alembic upgrade head
pytest            # fails if coverage drops below 70%
ruff check . && ruff format --check .
```

Frontend: `cd frontend && npm ci && npm run dev`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and on pushes to `main`: Ruff lint, pytest with a 70% coverage gate, Alembic upgrade/downgrade against PostgreSQL, the frontend build, and Docker image builds. The `deploy` job is a labelled placeholder until BEP-9 adds a real deployment. Do not commit credentials or claim a deployment URL until it is verified.

The team maintains only this repository.
