# Bolt's Journal

## 2024-05-22 - [N+1 Query in Dashboard]
**Learning:** When fetching top users and their chat counts, independent aggregations caused an N+1 query issue. Using `LEFT JOIN LATERAL` was more efficient than multiple subqueries or loop-based fetching.
**Action:** Always look for independent aggregations that can be consolidated or optimized using CTEs or Lateral Joins in PostgreSQL.
