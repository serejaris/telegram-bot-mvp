## 2024-05-23 - N+1 Query in Dashboard
**Learning:** `LEFT JOIN LATERAL` combined with `json_agg` is a powerful pattern to eliminate N+1 query problems when fetching parent entities (Chats) along with related child aggregates (Top Users, Last Message).
**Action:** Use this pattern whenever fetching a list of items that each require a "top N" or "most recent" related record.

## 2024-05-23 - Testing Database Performance
**Learning:** Mocking the cursor to count `execute` calls is a valid way to verify query count reduction in unit tests without a real database.
**Action:** Continue using `mock_cursor.execute.call_count` to verify performance optimizations in tests.
