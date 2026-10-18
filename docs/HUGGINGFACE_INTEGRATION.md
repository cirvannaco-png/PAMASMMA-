# PAMASMMA + Hugging Face: staged integration

## Current state

PAMASMMA already has a provider-neutral embedding service, PostgreSQL pgvector storage,
and knowledge ingestion with source provenance. The existing local provider is a
deterministic hashing fallback, not a trained semantic model.

This branch adds an optional adapter for a Hugging Face-hosted Text Embeddings
Inference (TEI) endpoint. It does not change the default provider or enable the
endpoint automatically.

## Configuration

Set these only in the deployment secret/configuration store, never in Git:

- `EMBEDDING_PROVIDER=huggingface`
- `HF_EMBEDDING_API_URL=https://<your-trusted-tei-endpoint>/embed`
- `HF_TOKEN=<least-privilege-token-with-inference-access>`
- Optional: `HF_EMBEDDING_TIMEOUT_SECONDS=20`

Use a trusted HTTPS endpoint. The adapter rejects non-HTTPS endpoints except
localhost, disables redirects, bounds request timeouts, rejects malformed and
non-finite vectors, normalizes embeddings, and pads vectors smaller than 1536
dimensions to the current PostgreSQL schema's vector(1536).

## Critical migration rule

Do not switch a populated production system from hashing/OpenAI embeddings to
Hugging Face embeddings until all stored vectors are regenerated with the same
model and version. Equal vector dimensions do not mean equal embedding spaces.
Memory rows and knowledge chunks must be re-embedded together, with a recorded
model identifier/version and an auditable migration. Keep the old provider active
until a backup is verified, reindexing completes, and retrieval evaluation passes.

## Acceptance tests before enabling

1. Adapter unit tests: direct vector, single-item batch, zero vector, wrong shape,
   non-finite values, and vectors above 1536 dimensions.
2. Endpoint tests: missing token/URL, timeout, HTTP error, invalid JSON, and no redirects.
3. Integration: insert and retrieve user memory and knowledge chunks using one
   consistent model version; verify user isolation and source locators.
4. Retrieval evaluation: compare current baseline vs candidate on a fixed, labelled
   query/chunk set. Report Recall@k, MRR/nDCG, latency, failure rate, and cost.
5. Operational: prove secrets are not logged, provider failure is observable, and
   rollback restores the previous model plus compatible vectors.

## PAMASMMA website and hosting plan

Recommended split:

- **Hugging Face Space:** optional model/demo surface or a lightweight private
  internal front end; do not treat a public Space as the security boundary.
- **Render:** FastAPI backend, PostgreSQL, Redis, background jobs, and durable
  application services.
- **Website:** authenticated browser UI calls the Render API over HTTPS. Use
  strict CORS, secure session/token handling, rate limits, audit logging, and
  server-side secrets. Do not expose database credentials or privileged tokens
  to browser JavaScript.

Before deployment, decide whether the Space is private and how user authentication
will work. Verify backup restoration, database reachability, authenticated health
checks, and a production smoke test before opening access.
