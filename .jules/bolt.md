## 2024-05-23 - Database JSON Aggregation
**Learning:** Consolidating N+1 queries using `json_build_object` and `json_agg` in PostgreSQL is effective but requires handling JSON parsing in Python if the driver behavior varies (e.g. mocking vs real `psycopg` 3).
**Action:** Always include fallback JSON parsing (`if isinstance(x, str): json.loads(x)`) when using JSON aggregation to ensure compatibility with both mocks and different driver configurations.
