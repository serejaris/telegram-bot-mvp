## 2024-05-23 - N+1 Query in Dashboard
**Learning:** Python loops executing SQL queries inside them (N+1 problem) are a major bottleneck. The `get_dashboard_data` function was executing `1 + 2*N` queries.
**Action:** Replaced loop-based fetching with a single complex SQL query using CTEs (`WITH`) and `LATERAL` joins to fetch aggregated data (last message, top users) in one go. Using `json_agg` allows returning nested lists from SQL.
**Result:** Reduced query count from `O(N)` to `O(1)`.
