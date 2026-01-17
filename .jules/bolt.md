## 2024-05-22 - [Optimized Dashboard Query]
**Learning:** Found significant N+1 query bottleneck in dashboard stats. Retrieving last message and top users for each chat triggered 2N+1 queries.
**Action:** Replaced loop with CTEs and LATERAL joins using json_agg to fetch all dashboard data in a single SQL query. Reduced 200+ potential queries to 1.
