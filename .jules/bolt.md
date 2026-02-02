## 2024-05-23 - N+1 Query Optimization with LATERAL Joins
**Learning:** In this codebase, dashboard data aggregation involving "latest item per group" (last message) and "top N items" (top users) caused N+1 query issues. Using PostgreSQL `LATERAL` joins combined with `LIMIT` allows fetching these per-row details efficiently in a single query, significantly outperforming iterative Python-side fetching.
**Action:** When needing per-row related data with limits (e.g., "top 3 users for each chat"), prefer `LEFT JOIN LATERAL (...) ON TRUE` over sequential queries in a loop.

## 2024-05-23 - Psycopg 3 JSON Handling
**Learning:** `psycopg` (v3) automatically deserializes `json` and `jsonb` columns into Python objects (lists/dicts). However, when using functions like `COALESCE` with `json_agg`, ensure the fallback value is cast to `::json` (e.g., `'[]'::json`) so the driver recognizes the column type correctly and performs the adaptation.
**Action:** Use `COALESCE(field, '[]'::json)` and be prepared to handle both deserialized objects and potential string fallbacks if the driver's adaptation behavior varies in edge cases (e.g. mocking).
