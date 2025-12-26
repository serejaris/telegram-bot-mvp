# Bolt's Journal ⚡

## 2024-05-23 - [Optimizing Dashboard Aggregations]
**Learning:** Optimizing N+1 queries in `get_dashboard_data` using `LATERAL JOIN` and `json_agg` is effective for reducing round trips. However, `psycopg` (v3) behavior with calculated JSON fields needs careful handling. While it usually adapts JSON types automatically, ensuring the code can handle both string (legacy/driver quirk) and list/dict (native adapter) responses prevents runtime errors.
**Action:** When using `json_agg` in complex queries, always include a safety check for the returned type (`isinstance(x, str)`) or ensure the database adapter is explicitly configured to return native Python objects for JSON columns, especially when working with calculated fields.
