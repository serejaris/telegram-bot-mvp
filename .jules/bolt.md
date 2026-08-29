## 2024-05-23 - [N+1 Query Optimization with LATERAL Joins]
**Learning:** For "top N items per group" queries (like fetching the last message and top users for each chat), looping in Python causes N+1 query performance issues. `LATERAL` joins in PostgreSQL allow efficient execution of per-row subqueries in a single database round-trip, significantly reducing overhead.
**Action:** When encountering loops that query the database for each item in a list, refactor using `LEFT JOIN LATERAL` to fetch all data in a single SQL query.
