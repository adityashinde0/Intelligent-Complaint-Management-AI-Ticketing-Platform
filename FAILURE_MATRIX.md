# Failure and Fallback Matrix

| Failure | Fallback Strategy |
|---|---|
| **LLM Unavailable** | Bypass conversational resolution. Present structured ticket intake form directly. |
| **Pinecone Unavailable** | Fallback to PostgreSQL full-text search across approved knowledge metadata, or bypass RAG and create a ticket. |
| **Low Retrieval Confidence** | Do not hallucinate. Ask a clarifying question or initiate ticket creation. |
| **Low Classifier Confidence** | Route ticket to a human triage queue with a generic parent category. |
| **No Eligible Agent** | Route to Overflow queue and trigger escalation policy immediately. |
| **Notification Failure** | Retry durably using the Transactional Outbox. Do not block ticket creation. |
| **Duplicate Request** | Check idempotency key (`client_message_id`). Return existing operation result. |
| **DB Transient Failure** | Exponential backoff and retry for the transaction block. |
| **Concurrent Ticket Update** | Return `409 Conflict` relying on optimistic concurrency control (`version` column). |
