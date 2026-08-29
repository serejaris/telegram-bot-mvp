## 2024-03-27 - N+1 Query in Dashboard Data
**Learning:** SQL aggregation with `json_agg` combined with CTEs is highly effective for solving N+1 problems in dashboard-like views where multiple related entities (last message, top users) are needed per parent entity (chat).
**Action:** When fetching lists of objects that require related sub-data (like "latest X" or "top Y"), always prefer CTEs and window functions over iterating in Python. Be careful with `json_agg` order - `ORDER BY` must be inside the aggregate function.
