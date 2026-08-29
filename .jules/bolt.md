## 2024-05-23 - N+1 Query in Dashboard Data
**Learning:** The `get_dashboard_data` function performs an N+1 query pattern (actually 2N+1), fetching chats first and then iterating to fetch the last message and top users for each chat. This can be optimized into a single query using `LATERAL` joins and `json_agg` to aggregate related data.
**Action:** Always look for loops around database queries. Use `LATERAL` joins or CTEs to fetch related data in a single round-trip, especially for dashboard-like views where multiple aggregates are needed per entity.
