## 2026-01-29 - [N+1 Query Optimization with LATERAL Joins]
**Learning:** For "latest item per group" queries (like last message per chat), standard `GROUP BY` is insufficient and often leads to N+1 queries. PostgreSQL `LATERAL` joins combined with `LIMIT 1` allow fetching these in a single efficient query, avoiding the N+1 problem completely while keeping the query readable.
**Action:** When fetching list views that require "latest X" or "top Y" sub-items for each row, always prefer `LATERAL` joins over loop-based queries or complex Window Functions if possible.
