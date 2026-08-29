## 2026-01-18 - N+1 Query in Dashboard
**Learning:** The dashboard statistics aggregation in `get_dashboard_data` was implemented with a loop over chats, triggering 2 additional queries per chat (Last Message + Top Users), leading to N+1 performance degradation.
**Action:** Use CTEs and `LATERAL` joins with `json_agg` to fetch hierarchical data (chat stats -> last message -> top users) in a single SQL query.
