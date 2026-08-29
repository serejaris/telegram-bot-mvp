## 2024-05-23 - Database Connection Reuse
**Learning:** Significant overhead comes from acquiring and releasing database connections from the pool multiple times for a single logical operation.
**Action:** When performing multiple DB operations in a sequence (like saving user, chat, then message), use a single connection/cursor context and pass it down to helper functions. Refactored helper functions to accept an optional `cur` argument to support both standalone and transactional usage.
