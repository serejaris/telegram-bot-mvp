## 2024-05-23 - CTEs for N+1 Query Optimization
**Learning:** Using Common Table Expressions (CTEs) combined with `json_agg` is a powerful way to eliminate N+1 query problems in PostgreSQL, especially when retrieving hierarchical data (like "top users per chat").
**Action:** When facing N+1 issues where child data needs to be fetched for multiple parents, consider using `WITH` clauses to aggregate child data first, then `LEFT JOIN` it to the parent query.
