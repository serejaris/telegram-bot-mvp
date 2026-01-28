## 2024-05-22 - SQL Optimization: N+1 with LATERAL
**Learning:** Using `LATERAL` joins combined with `json_agg` allows fetching complex hierarchical data (like "top N items per group") in a single query, eliminating N+1 problems.
**Action:** Replace loops of queries with `LATERAL` subqueries when fetching details for a list of items.
