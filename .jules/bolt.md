## 2026-01-27 - N+1 Query Optimization in Dashboard
**Learning:** Consolidating multiple `SELECT` queries into a single query using `LATERAL` joins and `json_agg` can significantly reduce database round-trips (from N+1 to 1). Using `json_agg` allows fetching nested related data (like "Top Users") without a separate query loop.
**Action:** When optimizing dashboard or list views where each item requires related aggregated data, prefer CTEs and `LATERAL` joins over iterative Python loops. Ensure `json` handling accounts for driver differences (string vs object).
