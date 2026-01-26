## 2024-05-22 - SQL Optimization with LATERAL Joins
**Learning:** Using `LATERAL` joins combined with `json_agg` allows fetching complex hierarchical data (like "last message" and "top users" per chat) in a single query, effectively solving N+1 problems where window functions or simple joins are insufficient or too complex to group.
**Action:** When facing N+1 queries involving "top N" or "latest N" items per parent row, prefer `LEFT JOIN LATERAL (...)` over iterating in application code.
