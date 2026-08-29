## 2024-03-24 - N+1 Query Optimization in get_dashboard_data
**Learning:** Combining independent aggregations (Total/Today messages) and row-based joins (Last Message, Top Users) in a single query requires careful isolation using `LATERAL` joins or CTEs. Joining `messages` directly to `chats` for aggregations *before* `LATERAL` joins caused a row explosion, multiplying the result set by the number of messages before grouping, which would have been a significant performance regression despite reducing query count.
**Action:** Always verify row counts and explain plans when optimizing complex N+1 queries. Use `LATERAL` subqueries for aggregations to keep the main query cardinality equal to the primary table (Chats).

## 2024-03-24 - JSON Aggregation Ordering
**Learning:** When using `json_agg` in PostgreSQL to fetch "top N" items, the order is not guaranteed unless `ORDER BY` is explicitly included *inside* the aggregate function (e.g., `json_agg(... ORDER BY ...)`).
**Action:** Always specify ordering within `json_agg` when the order of the resulting list matters for the application logic.
