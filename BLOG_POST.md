# Why I picked pgvector over Pinecone for my RAG chatbot

*A trade-off post from building [DocuPilot](https://github.com/oceanja/RAG-DOC-CHATBOT) — a self-hostable RAG chatbot that drops onto any docs site via a `<script>` tag.*

When I started building DocuPilot, the obvious choice for vector storage was Pinecone. It's what most RAG tutorials show, the SDK is one line, and the free tier exists. Two days in, I switched to **pgvector** — Postgres with a vector type extension — and I'm glad I did.

Here's the actual reasoning, with the numbers from my project.

---

## The decision matrix

DocuPilot's scale: **a few projects, ~50–500 pages each, ~3–5 chunks per page**. That's **at most ~10,000 chunks per project**, and unlikely to ever cross 1 million chunks across all projects on a single instance. This is the key constraint.

| Criterion | pgvector | Pinecone |
|---|---|---|
| Infra to run | One DB (already need it for metadata) | Two services (Postgres + Pinecone) |
| Cost (my scale) | $0 (Supabase free tier) | $0 free, then $70/mo starter |
| Vendor lock-in | None — SQL is SQL | High — proprietary API |
| Performance < 1M vectors | Comparable | Comparable |
| Performance > 10M vectors | Degrades | Wins |
| Filtering by metadata | Native SQL `WHERE` | Limited filter API |
| Hybrid search (BM25 + vector) | One JOIN away | Custom pipeline |
| Joining citations to docs | Single SQL query | Multi-step round trip |

The two rows that matter most for a docs-bot use case: **metadata filtering** and **joining citations**.

## The actual problem this solved

Here's a query from DocuPilot's [`retrieval.py`](backend/app/services/retrieval.py):

```python
stmt = (
    select(Chunk, Document, distance)
    .join(Document, Chunk.document_id == Document.id)
    .where(Chunk.project_id == project_id)
    .where(Chunk.embedding.is_not(None))
    .order_by(distance)
    .limit(k)
)
```

In one round trip I get:
1. Top-K closest chunks (by cosine distance via `<=>`)
2. Scoped to the right project (metadata filter)
3. Joined to the parent document (for citation title + source URL)

With Pinecone I'd do this in **three steps**: query the index → get chunk IDs → fetch metadata from Postgres → fetch parent docs. Three round trips, three points of failure, more code.

pgvector lets me write the obvious SQL.

## The ops side nobody talks about

DocuPilot's other ops surface: ARQ workers, projects/documents/chunks/questions tables, alembic migrations. All Postgres. Adding Pinecone means:

- A second API key in env vars
- A second rate limit to monitor
- A second "what state is this in?" question during incidents
- A second thing to mock in tests

For a sub-million-vector project, **the cost of operating two stores exceeds the performance benefit**. The math is different at 10M+ vectors, where pgvector's ivfflat index starts to struggle and Pinecone's HNSW pulls ahead. But you should hit that scale first before paying the operational tax.

## The performance reality check

For my scale, retrieval is **~30ms** with the ivfflat cosine index (`lists=100`, 47–1500 chunks). The bottleneck is Gemini's embedding call (~200ms) and chat generation (~1s for first token), not vector search.

```sql
CREATE INDEX idx_chunks_embedding ON chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

I also chose to use Gemini's **MRL-truncated 768-dim embeddings** instead of full 3072. Same retrieval quality (Matryoshka Representation Learning is designed for this), quarter the index size, and within pgvector's ivfflat 2000-dim limit. Two wins from one parameter.

## When you should pick Pinecone instead

I'm not saying pgvector is always right. Pick Pinecone when:

- You're past **10M vectors** and your queries are getting slow
- You need **multi-tenant isolation** at the index level
- You want **managed sharding** without thinking about it
- You're using a serverless backend (Vercel/Lambda) and don't want to run Postgres

For everyone else building something at startup or portfolio scale: **one Postgres beats two services**.

---

## The bigger lesson

It's tempting to pick the "specialist" tool because tutorials use it. But the question isn't "what's the best vector database?" — it's **"what's the simplest stack that meets my constraints?"** For DocuPilot, with sub-million vectors and a need to join citations to source docs, the simplest stack happened to be the boring one: Postgres.

The default-to-Postgres heuristic has aged well across the last 30 years of web engineering. It's still working in 2026.

---

*Code: [github.com/oceanja/RAG-DOC-CHATBOT](https://github.com/oceanja/RAG-DOC-CHATBOT) · Live demo: [rag-doc-chatbot.vercel.app](https://rag-doc-chatbot.vercel.app/) · I'm an early-career engineer based in India — open to SDE / full-stack / AI engineering roles. Reach me on [LinkedIn](https://www.linkedin.com/in/).*
