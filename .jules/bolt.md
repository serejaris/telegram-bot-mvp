## 2026-01-25 - N+1 Query Optimization with Lateral Joins
**Learning:** Using `LEFT JOIN LATERAL` combined with `json_agg` allows fetching related "top N" or "latest 1" items for multiple parent rows in a single query, effectively solving N+1 problems without complex window functions or separate queries.
**Action:** When seeing loops that execute SQL queries for each item in a list (e.g., fetching details for each chat in a dashboard), convert them to a single query using `LATERAL` joins to bundle the related data.
