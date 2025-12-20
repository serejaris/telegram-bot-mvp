## 2024-05-22 - [Optimizing N+1 Queries in Dashboard]
**Learning:** `LEFT JOIN LATERAL` combined with `json_agg` is a powerful pattern in PostgreSQL to solve N+1 query problems where you need to fetch related subsets (e.g., "top N items") for each parent row. It allows pushing the loop logic into the database engine, significantly reducing round-trips.
**Action:** When encountering loops that query related data per item (especially with limits or sorting), replace them with a single query using `LATERAL` joins.
