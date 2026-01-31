## 2024-05-23 - N+1 Query in Dashboard Data
**Learning:** The `get_dashboard_data` function was performing 1 + 2N queries (fetching chats, then looping to fetch last message and top users for each). This N+1 pattern significantly impacts performance as the number of chats grows.
**Action:** Replaced the loop with a single optimized SQL query using CTEs and `LATERAL` joins to fetch all required data in one round-trip. Use `LATERAL` joins with `LIMIT` for "top N items per group" queries in PostgreSQL.
