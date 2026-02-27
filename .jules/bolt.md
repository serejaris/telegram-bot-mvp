## 2025-02-18 - [Optimization] N+1 Query in Dashboard Data
**Learning:** The dashboard was executing N+1 queries (actually 2N+1) to fetch "last message" and "top users" for each chat. Using `LATERAL` joins and `json_agg` in PostgreSQL allowed fetching this hierarchical data in a single efficient query.
**Action:** When fetching summary data for a list of items (like chats), always verify if subsequent queries are running in a loop. Use `LATERAL` joins or CTEs to aggregate sub-data into the main query.
