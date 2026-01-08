## 2024-05-23 - [N+1 Query in Dashboard]
**Learning:** Detected and fixed a classic N+1 query problem in `get_dashboard_data`. The original code iterated over chats and executed 2 additional queries per chat (getting last message and top users). This would result in 1 + 2*N queries.
**Action:** Replaced the loop with a single complex SQL query using Common Table Expressions (CTEs), `DISTINCT ON` for the last message, and `json_agg` with window functions for top users. Reduced queries from O(N) to O(1).
**Note:** When using `psycopg` 3, JSON aggregation results are automatically deserialized, but mocks in tests might return strings, so defensive coding `if isinstance(x, str): json.loads(x)` is useful.
