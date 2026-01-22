## 2024-05-22 - N+1 Query in Dashboard
**Learning:** `LATERAL` joins are essential for optimizing "Top N per group" queries in PostgreSQL, replacing N+1 query patterns with a single efficient query.
**Action:** Always check for N+1 queries in loops that fetch related data (like "last message" or "top users") and use `LATERAL` or CTEs to consolidate them.
