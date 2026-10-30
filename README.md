# Enterprise AI Knowledge & Automation Platform

A working portfolio demonstration for AI / Solutions Architect and Forward Deployed Engineer roles. All customers, orders, tickets and policies are synthetic. This repository makes no claim of customer production deployment or experience.

The application combines document evidence with operational records. A browser UI shows citations, source excerpts, retrieval mode, MCP tools and the graph trace. FastAPI serves the UI and APIs, Qdrant persists document vectors, and LangGraph routes each request through knowledge retrieval, enterprise tools, both, or clarification.

## Run locally

Python 3.12+ recommended. From the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
Copy-Item .env.example .env
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On macOS/Linux use `python3`, `.venv/bin/python`, and `cp .env.example .env` instead. Open [the UI](http://127.0.0.1:8000), enter your `APP_API_KEY`, and connect. The development default is `local-demo-key-change-before-hosting`. Synthetic records and sample policy documents are seeded automatically. `/health` indicates startup completed; `/api/status` reports indexed chunks. Interactive API documentation is at `/docs`, and the schema at `/openapi.json`. The public Swagger page requires its external CDN assets; restrictive application CSP is relaxed only for this documentation page. Supply headers when using APIs outside the UI.

Try:

- What is the escalation policy for a priority-one support incident?
- What does the refund policy say about enterprise subscriptions?
- What is the status of order ORD-1003?
- Show the open service tickets for customer CUST-002.
- According to policy, what should happen next for ticket TKT-1001?

## Embeddings and generation

The default `EMBEDDING_MODE=fastembed` uses the local ONNX model `BAAI/bge-small-en-v1.5` (384 dimensions). Local development downloads it into `MODEL_CACHE_PATH` (default `data/models`) on first use; the Docker build pre-downloads it into the image so ephemeral cold starts can use the bundled weights. A missing cache needs outbound model-download access, not an API key. Model initialization failure fails startup rather than silently changing retrieval semantics. Windows installation includes an app-local MSVC runtime wheel, avoiding a system-wide runtime installation.

`EMBEDDING_MODE=offline` is an explicit, deterministic feature-hashing lexical baseline. It runs without external services and is useful for smoke tests; it is **not semantic retrieval**. Modes use separate versioned Qdrant collections. Similarity thresholds are heuristics, not calibrated confidence. Retrieval relevance and generation can still be wrong.

With no `OPENAI_API_KEY`, answers display retrieved excerpts verbatim with citations and separate JSON operational records. Set `OPENAI_API_KEY` securely in the untracked `.env` (or hosting secret manager) to enable grounded generation and LLM function selection. `OPENAI_MODEL` configures the model. Function calls are restricted to identifier-validated read-only calls; the model cannot introduce arbitrary IDs or tool names. An unavailable model produces a visible warning and falls back to evidence. Model requests send the question and retrieved synthetic data to the provider. No provider credentials are needed for the local extractive demonstration.

## Ingestion and retrieval

Upload UTF-8 TXT/Markdown or text-based PDF through the UI or `POST /api/ingest`. Uploads are limited to 5 MiB and 200 PDF pages. Scanned PDFs require upstream OCR. Source filenames, page numbers, chunk indices and text are retained in Qdrant; original files are not stored. Documents are split into 220-word windows with 40-word overlap (step 180), balancing short policy paragraphs with bounded context. PDFs are chunked page by page to preserve citations. These are word windows, not tokenizer windows.

Replacement uses stable UUIDs and deletes prior chunks for the same source after parsing/embedding succeeds; re-indexing is idempotent and removes stale tail chunks. Replacement is serialized within the process but not transactional across Qdrant delete/upsert; a database outage during replacement can leave an incomplete source. Upload the source again to recover. Sample filenames are reserved in practice: samples re-index on restart, replacing uploads with those names. Small demo documents are embedded in memory; large corpus ingestion needs a queue and streaming batches.

Retrieval uses cosine nearest neighbors, configurable `top_k` (1–10), and a score threshold of 0.20. Each returned excerpt has `[S#]`, filename, page, chunk and score. Insufficient evidence produces an abstention. Citation-ID checks reject unknown or missing policy citation IDs in model output; they do not prove entailment or eliminate hallucinations.

## MCP and operational data

`app/mcp_server.py` implements the MCP protocol with the official SDK over stdio. It exposes `get_customer`, `get_order_status`, `get_ticket`, and `list_customer_tickets`. The orchestrator's MCP client starts an isolated Python subprocess, initializes an MCP session, and calls a named tool. The MCP server uses authenticated HTTP to the FastAPI enterprise endpoints. No database access bypasses this path. A fresh subprocess per call keeps lifecycle simple; pooling is a future latency improvement.

MCP provides tool discovery/schema and protocol boundaries that a direct REST call would not. REST remains the underlying enterprise integration contract. Replace adapter HTTP calls to integrate another order/support platform. The adapter needs `API_BASE_URL` and `ENTERPRISE_API_KEY`; it defaults to the same local service. The tool server and API must share environment configuration. All operational capabilities are read-only. No write tool is exposed, so no approval workflow is necessary in this release.

The graph has typed state and conditional edges: `route → tools → retrieve → generate → check`, skipping tools/retrieval as appropriate. Tools precede retrieval on the combined path so ticket priority can improve policy retrieval. Routing is deterministic and inspectable; optional LLM function calling selects from validated operational calls. No autonomous loops; at most four tool calls and ten graph steps. Questions without a recognized policy intent or record identifier request clarification.

## Tests and evaluations

```powershell
.venv/Scripts/python -m pytest -q
# With the application running separately:
.venv/Scripts/python scripts/evaluate.py
```

Tests cover API authentication, validation, data lookup, ingestion replacement, upload size/type rejection, PDF text extraction, graph routing, tool failure, citation guards, model function-call argument restrictions and empty-knowledge abstention. Live evaluations exercise seven acceptance questions through HTTP and real MCP subprocesses. The evaluator writes `docs/evaluation-results.json`. Run `python scripts/semantic_evaluate.py` to evaluate real semantic ranking on three paraphrases; results are in `docs/semantic-evaluation-results.json`. These are small regression checks, not broad claims of answer quality. Credentialed model behavior needs live evaluation on your target corpus; model unit tests use mocks. CI runs offline tests and the live MCP evaluation. `requirements.lock` captures tested dependency versions; `requirements.txt` expresses the compatible direct dependency ranges.

## Deployment

The initial Render portfolio demo uses **one Free web service, no disk, and no managed datastore**, defined in `render.yaml`. See the [Render deployment guide](docs/render-deployment.md). It retains semantic retrieval with one embedding thread and one concurrent chat query to reduce resource use. No paid Render resources have been created.

The filesystem is disposable. Every startup creates missing synthetic SQLite records and re-indexes repository-managed `.md`, `.txt` and text-based `.pdf` files directly in `samples/` into the configured Qdrant collection. Stable IDs and source replacement make this safe on an existing store as well as a blank one. Startup completes before `/health` is served; empty/missing samples or failed indexing fail startup. UI uploads disappear when local storage resets; commit lasting demo documents to `samples/` instead. Never commit runtime SQLite/vector files or secrets.

Render Free services sleep after 15 idle minutes and lose local files on restart, redeploy and spin-down; cold starts and workspace usage limits apply. See [Render's current free-service limits](https://render.com/docs/free). The image includes the embedding model, but Render build/startup and actual free-instance memory use still need verification. No paid upgrade should be made automatically if resources prove insufficient. An optional `OPENAI_API_KEY` can incur provider charges; it is not needed for the initial extractive demo.

To publish: review/commit/push these files to the GitHub repository's `main` branch, connect Render to that repository (through the integration or dashboard), and create a Blueprint after confirming Free/no disk. Use Render-generated API keys. Automatic deployments remain disabled; no public service has been created from this working tree.

Local Docker Compose can optionally retain data in its named volume:

```sh
cp .env.example .env
# Set independent random APP_API_KEY and ENTERPRISE_API_KEY in .env.
docker compose up --build -d
```

The image uses a non-root user and one Uvicorn worker. Compose binds to localhost; its optional local persistence is independent of the disk-free Render profile. Keep one process with Qdrant local mode because multiple workers cannot share its storage lock. Later, set `QDRANT_URL` and `QDRANT_API_KEY` for Qdrant Cloud, or mount a volume and configure `QDRANT_PATH`, `ENTERPRISE_DB_PATH` and `MODEL_CACHE_PATH` for local persistence. No architecture redesign is needed. Demo SQLite can always be reseeded; preserving non-synthetic operational records would need a durable backend. Production use also needs individual identity/RBAC, quotas, ingress size limits, document isolation and tenant controls. Logs include request IDs, route traces, status and latency without intentionally recording keys or prompts.

See [architecture and tradeoffs](docs/architecture.md). Public cloud deployment requires a selected hosting account and secrets; local execution and an image recipe do not establish a public deployment.
