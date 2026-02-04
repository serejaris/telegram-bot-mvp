## 2024-05-22 - Solving N+1 with LATERAL Joins
**Learning:** When aggregating multiple independent related data sets (like "last message" and "top users") for a list of items, `LATERAL` joins combined with `json_agg` are essential to prevent row explosion and N+1 queries. Psycopg 3 usually handles JSON deserialization, but fallback to `json.loads` is safe.
**Action:** Use `LEFT JOIN LATERAL` for fetching specific related items (limit 1) or sub-aggregations in the main query.
