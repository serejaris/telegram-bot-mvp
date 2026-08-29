## 2024-05-23 - Optimizing Dashboard N+1 Queries
**Learning:** Using `LEFT JOIN LATERAL` combined with `json_agg` is a powerful pattern to eliminate N+1 query problems in dashboards. It allows fetching parent records along with "top N" or "latest" child records in a single round-trip, leveraging PostgreSQL's JSON capabilities which `psycopg` automatically deserializes.
**Action:** Apply this pattern whenever a view requires iterating over a list of entities to fetch their related "summary" or "top" data.
