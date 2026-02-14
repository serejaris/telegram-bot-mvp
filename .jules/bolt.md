## 2024-05-23 - N+1 Query Optimization with LATERAL Joins
**Learning:** Python loops executing SQL queries for each item (N+1 problem) can be replaced by a single query using `LEFT JOIN LATERAL`.
**Action:** Use `LEFT JOIN LATERAL` combined with `json_agg` to fetch related list data (like "top users") for each parent row in one go. Handle `COUNT` aggregations in separate subqueries/CTEs to avoid row explosion when joining multiple 1-to-N relationships.
