## 2024-10-26 - N+1 Query Pattern in Dashboard
**Learning:** The dashboard data retrieval (`get_dashboard_data`) exhibited a classic N+1 query pattern, executing 1 query for chats and then 2 additional queries per chat to fetch the last message and top users. This scales linearly with the number of chats, causing performance degradation.
**Action:** Use `LATERAL` joins combined with `json_agg` (and CTEs for clarity) to fetch nested data in a single database round-trip. This approach is significantly more efficient for PostgreSQL.
