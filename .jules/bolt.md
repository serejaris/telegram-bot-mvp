## 2024-05-23 - [N+1 Query Optimization with LATERAL JOINs]
**Learning:** In PostgreSQL, replacing iterative N+1 queries with `LEFT JOIN LATERAL` combined with `json_agg` is extremely effective for fetching related aggregate data (like "last message" or "top users") for a list of items.
**Action:** When needing complex per-row aggregates that would otherwise require separate queries or subqueries, use `LEFT JOIN LATERAL` to calculate them efficiently in a single pass. Ensure `json_agg` is used to bundle list-like relations (e.g., top 3 users) into a single column.
