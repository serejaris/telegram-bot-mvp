## 2026-01-15 - N+1 Query in Dashboard
**Learning:** `get_dashboard_data` was performing N+1 queries (2 additional queries per chat) causing performance degradation as chat count grows.
**Action:** Use CTEs and `json_agg` to fetch all related data (last message, top users) in a single query to prevent row explosion and multiple round-trips.
