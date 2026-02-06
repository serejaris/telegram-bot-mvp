## 2024-05-22 - N+1 Query Elimination in Dashboard
**Learning:** The `get_dashboard_data` function suffered from a severe N+1 query issue (1 + 2N queries).
**Action:** Replaced the iterative fetching of last messages and top users with `LATERAL` joins and `json_agg` in a single query.
