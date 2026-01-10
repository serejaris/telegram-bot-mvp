## 2024-05-22 - Optimizing N+1 Queries with CTEs and json_agg
**Learning:** When fetching hierarchical data (e.g., chats -> last message, chats -> top users), avoid N+1 queries by using Common Table Expressions (CTEs) and PostgreSQL's `json_agg` function.
**Action:** Consolidate multiple queries into a single SQL statement. Use `DISTINCT ON` for "latest item per group" and `json_agg` with `ORDER BY` inside for ordered nested lists.
