# Design decisions and deviations

These are baseline decisions and planned limitations, not claims that code exists. Replace Actual with verified implementation evidence as work lands.

| Item | Document and section | Planned | Actual | Reason |
| --- | --- | --- | --- | --- |
| Roles | Updated task plan | PDF: Abhiram DevOps, Nishkal Auth | User-confirmed assignment: Nishkal DevOps, Abhiram Auth | Explicit user instruction |
| token_version | SAD 3.6; F-003 | Add users.token_version default 0 | Included in design; code pending | Immediate all-session logout |
| department | SAD 3.6; F-004 | Nullable profile field | Included in design; code pending | Profile UI |
| deleted_at | SAD 3.6; F-013 | Nullable listing timestamp | Included in design; code pending | Soft deletion |
| GET /listings/mine | SAD 4.3; F-011 | Owner-only non-deleted listings | Included in design; code pending | My Listings UI |
| Rate limiter | SAD 3.5; SR-006 | In-memory email/IP window | Not implemented | Single-instance baseline; resets on restart |
| Active-exchange guard | SRS 6; TC-LST-07 | Mock in Sprint 1, real query in Sprint 2 | Not implemented | Exchange schema arrives in Sprint 2 |
| Hosting | SAD 4.4 | HTTPS backend, static frontend, persistent Postgres | Provider not selected | Confirm availability and limits at deployment |
| NF-002 / NF-005 targets | SRS 5 | Proposed 99% measured availability and p95 matching <=2s | Pending team review | Source plan identifies metrics without numerical values |
| Matching policy | SAD 3.5.1 | Proposed 70/20/10 relevance/location/condition score | Pending Sprint 2 review | Explicit deterministic implementation baseline |
| API errors and data safety | SAD 4.3 | Consistent validation envelope; reject profile privilege changes; bcrypt byte limit | Not implemented | Resolve edge cases without weakening plan requirements |
