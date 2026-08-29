## 2024-05-23 - N+1 Query Optimization in `get_dashboard_data`
**Learning:** Consolidating multiple queries into a single SQL query using CTEs and `json_agg` drastically reduces database roundtrips for dashboard data.
**Action:** When fetching hierarchical data (e.g., parent with child lists), prefer using `json_agg` with subqueries or CTEs over iterating in Python.
