## 2024-05-23 - N+1 Query in Dashboard
**Learning:** `get_dashboard_data` suffered from an N+1 query problem, fetching details for each chat individually. This pattern scales linearly with the number of chats, which is a major bottleneck.
**Action:** Replaced loop-based queries with a single SQL query using CTEs, `LEFT JOIN LATERAL` for retrieving the last message, and `json_agg` for aggregating top users. This reduces database round-trips from `1 + 2N` to `1`.
