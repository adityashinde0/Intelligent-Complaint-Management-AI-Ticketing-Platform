# Vector Drift Management

## 1. Vector Versioning
Every vector inserted into Pinecone MUST contain:
- `tenant_id`
- `document_id`
- `chunk_id`
- `document_version`
- `embedding_model`
- `embedding_version`
- `language`
- `authority_level`

## 2. Types of Drift
- **Embedding Drift:** When the embedding model is updated, the spatial relationship of the vectors changes. A shadow evaluation namespace must be created before promoting a new model.
- **Corpus Drift:** When the underlying knowledge base receives extensive updates, making older chunks stale.
- **Query Drift:** When customer vocabulary changes (e.g., describing a new product defect). Lexical/Semantic drift requires re-tuning the reranker.

## 3. Promotion & Rollback
- Vectors from different embedding models will NEVER reside in the same active search namespace.
- Rollbacks are performed by querying the previous active namespace index.
