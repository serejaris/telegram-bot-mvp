## 2024-05-23 - N+1 Query in Dashboard
**Learning:** `get_dashboard_data` was fetching last messages and top users in a loop for each chat, leading to N+1 queries.
**Action:** Use CTEs and `json_agg` (with `ORDER BY` inside `json_agg` for deterministic output) to fetch all related data in a single complex query. This reduces database round-trips from `1 + 2N` to `1`.
