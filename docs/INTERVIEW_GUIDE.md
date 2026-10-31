# Interview Guide

Use these answers to explain this repository at two levels: a concise recruiter answer and a deeper technical discussion. All examples refer to the synthetic Enterprise AI Knowledge & Automation Platform. They are suggested descriptions of the portfolio work, not claims of prior production customer experience.

For file-level traces, see [Architecture Walkthrough](ARCHITECTURE_WALKTHROUGH.md). The application is deployed at [Enterprise Intelligence](https://enterprise-ai-knowledge-automation.onrender.com/).

## 1. Tell me about the project

**Recruiter answer:** “I built a portfolio application that answers policy questions with source evidence and retrieves synthetic operational records through tools. It brings together Python, FastAPI, Qdrant, LangGraph, MCP, a browser UI, tests and a working Render deployment.”

**Technical answer:** `app/main.py` owns FastAPI and lifecycle; `app/knowledge.py:Knowledge` owns parsing/vector retrieval; `app/workflow.py:make_graph()` owns routing and response construction. The MCP adapter uses a real stdio session and authenticated HTTP to a seeded SQLite-backed REST service. The deployed profile uses semantic embeddings and extractive responses. Hosted LLM generation/function selection is implemented but requires a provider key and has not been verified live in the initial demo.

**Experience boundary:** “This is a synthetic portfolio demonstration. It shows the implementation I can walk through; I would discuss customer production work separately and accurately.”

## 2. What is RAG, and where is it implemented?

**Recruiter answer:** “RAG retrieves relevant source material before constructing an answer. In this project, policy answers include the retrieved evidence so someone can inspect where the information came from.”

**Technical answer:** `Knowledge.ingest()` parses/chunks/embeds documents into Qdrant; `Knowledge.retrieve()` embeds the question and retrieves similar chunks. The graph's `retrieve()` node supplies citations to `generate()`. Without a provider key, generation is deterministic excerpt presentation. With a key, a model can synthesize from that evidence. Retrieval does not update model weights and does not eliminate unsupported answers.

## 3. How do embeddings work here?

**Recruiter answer:** “Embeddings represent text numerically so related questions and policy passages can be compared. The demo generates semantic embeddings locally, without sending the documents to an embedding API.”

**Technical answer:** FastEmbed runs `BAAI/bge-small-en-v1.5` through ONNX and returns 384-dimensional vectors. The same backend embeds documents and queries. Collection names separate semantic and offline modes. `EMBEDDING_MODE=offline` is a normalized token-hashing baseline, not semantic retrieval. A different model requires a compatible new/rebuilt index; identical dimensions do not establish semantic compatibility.

## 4. Why Qdrant instead of a normal database search?

**Recruiter answer:** “Qdrant handles vector similarity and retains the source metadata needed to show evidence. SQLite serves a different purpose: exact customer, order and ticket records.”

**Technical answer:** `Knowledge.__init__()` configures cosine vectors and selects local-path or remote-URL Qdrant. Payloads contain source, page, chunk and text. `query_points()` performs the similarity lookup; the application requests up to `top_k` results above 0.20. Local Qdrant avoids a separate demo service. Do not imply this deployment is a distributed Qdrant cluster or has benchmarked large-scale ANN performance. No current query-time tenant/source filtering is implemented.

## 5. How did you choose chunk size and overlap?

**Recruiter answer:** “I used short overlapping windows to keep policy context together while keeping retrieval manageable. The values are explicit and easy to evaluate.”

**Technical answer:** `Knowledge.ingest()` uses 220 words with a 180-word step: 40-word overlap for full windows. PDFs are split page by page; Markdown/text use page one. This is whitespace splitting, not token-aware or structure-aware parsing. It can separate headings from clauses and flatten tables. I would tune it against labeled retrieval cases and add structural parsing where document layout matters, rather than assert these defaults are universally optimal.

## 6. What makes retrieval semantic? Is there a relevance check?

**Recruiter answer:** “The semantic model can match paraphrases rather than requiring the exact policy wording. There is a basic similarity threshold, but it is not a confidence score.”

**Technical answer:** FastEmbed encodes query/passage meaning, and Qdrant ranks cosine similarity. `scripts/semantic_evaluate.py` checks three paraphrases against the expected top source. The fixed 0.20 cutoff is the only retrieval relevance gate; there is no reranker or calibrated answerability classifier. Broad or unrelated questions may still retrieve policy text. Deterministic routing also limits which paraphrases reach retrieval at all.

## 7. How do grounding and citations prevent hallucinations?

**Recruiter answer:** “They make evidence inspectable and constrain the response, but they do not guarantee that every statement is supported.”

**Technical answer:** Without a model key, the system presents actual excerpts with `[S#]` references and separates operational JSON. Optional model generation receives only supplied evidence plus instructions to abstain when it is insufficient. The guard inside `generate()` rejects unknown citation IDs and missing citations when policy excerpts exist. It only requires at least one citation, not one per claim, and does not verify entailment. The final `check()` node adds a trace/warning; it is not another answer-quality model. Failure falls back to the source excerpts.

## 8. What does LangGraph contribute?

**Recruiter answer:** “It makes the different execution paths explicit. A question can need policy retrieval, an operational lookup, both, or clarification, and the UI shows which path ran.”

**Technical answer:** `StateGraph(State)` in `make_graph()` registers `route`, `tools`, `retrieve`, `generate` and `check`. Conditional edges select branches after routing and tools. On `both`, tools precede retrieval so actual ticket priority can enrich the search. The graph is acyclic, uses a ten-step recursion bound and executes at most four sequential tool calls. It is not a decorative framework dependency, but LangGraph is not doing semantic intent classification here.

## 9. Is this an agent or a workflow?

**Recruiter answer:** “It is a bounded workflow with optional model-assisted tool selection. I chose predictable behavior rather than an unrestricted autonomous agent.”

**Technical answer:** `route()` uses substrings and record-ID regexes. No model plans arbitrary steps, no node loops, and no checkpointed memory or human-approval process is configured. With a key, a model selects from allowed function calls, but the application checks its proposals against deterministic candidates. I would introduce an agent loop only for a use case that actually needs iterative planning and can support its authorization, evaluation and execution controls.

## 10. What state is maintained?

**Recruiter answer:** “The system keeps the question, evidence, operational results and trace together during one request. It does not retain a conversation between requests.”

**Technical answer:** The `State` TypedDict includes question, top-k, route, citations, operational data, tools, warnings, answer, trace and actual generation mode. It is a typing contract with optional fields, not runtime validation of intermediate state. Pydantic models validate external requests/responses. There is no LangGraph checkpointer, durable conversation store, session history or cross-request agent memory.

## 11. What is MCP, and why use it here?

**Recruiter answer:** “MCP gives the AI workflow a consistent tool interface. In this demo, the tools retrieve records through a separate adapter rather than letting the orchestrator read the operational database directly.”

**Technical answer:** `app/mcp_client.py:call_tool()` starts `python -m app.mcp_server`, opens a stdio `ClientSession`, initializes it and calls a tool. `FastMCP` decorators expose four typed tools. The server's `get()` translates them into authenticated HTTP requests. The client explicitly passes the backend URL and enterprise key to the child process; relying on inherited environment values previously failed isolation testing. MCP supplies the protocol/tool boundary; it is not an LLM, business database, authorization system or sandbox.

## 12. How is MCP different from REST?

**Recruiter answer:** “MCP is the interface the workflow uses to invoke tools; REST is how those tools reach the enterprise data service.”

**Technical answer:** `get_order_status` is an MCP tool that calls `GET /enterprise/orders/{order_id}` through `httpx`. The REST API validates access and returns an `Order` model from SQLite. MCP retains tool names, schemas, session initialization and standardized result handling. A direct REST call would be simpler for one fixed client, but this portfolio intentionally demonstrates the reusable adapter boundary. The additional subprocess/session is a measurable latency and memory trade-off.

## 13. Does the model actually call tools?

**Recruiter answer:** “The deployed demo runs real MCP tools through deterministic routing. An optional hosted-model path can select function calls, but it cannot introduce arbitrary identifiers or actions.”

**Technical answer:** `TOOL_DEFINITIONS` describes read-only functions for OpenAI's Chat Completions API. When configured, `tools()` requests function selection, parses the proposed arguments and accepts them only if every tuple exists in the deterministic candidate list. `ALLOWED` provides a second name check. Calls are capped at four; there is no general autonomous assistant/tool loop. Live provider selection was not tested without an API key, so the tested function-selection claims are based on mocks. The MCP execution itself was verified on Render.

## 14. What enterprise integration exists?

**Recruiter answer:** “It is a simulated enterprise integration using synthetic customers, orders and tickets. It demonstrates the adapter contract without claiming a Salesforce or ServiceNow deployment.”

**Technical answer:** `enterprise.seed()` creates SQLite tables and sample rows. REST functions `customer()`, `order()`, `ticket()` and `tickets()` expose validated responses under `/enterprise`. The MCP server authenticates with `X-Enterprise-Key`; the user-facing API uses `X-API-Key`. Missing records are 404 and invalid ticket status is 422. Replacing this service requires actual connector authentication, pagination, failure mapping, rate limits and permissions. The current orchestrator lists open customer tickets; it does not fully interpret arbitrary ticket-status requests.

## 15. How do you evaluate it?

**Recruiter answer:** “I test the important paths and failure behavior, then run live acceptance questions. I separate that evidence from any claim of broad answer quality.”

**Technical answer:** The verified suite has 14 passing cases covering authentication, API validation, PDF extraction, overlap/replacement, source metadata, empty retrieval, graph/tool failures, citation guards, function-argument restrictions, startup rebuilding, Render configuration and MCP environment forwarding. `scripts/evaluate.py` checks seven requests through HTTP and real MCP subprocesses. `scripts/semantic_evaluate.py` tests three top-source paraphrase rankings. These are not comprehensive grounding, adversarial-security or load evaluations. Next metrics would include labeled recall@k, answerability/abstention, per-claim support, tool correctness and p50/p95 latency by route.

## 16. What observability is implemented?

**Recruiter answer:** “Every request has an ID, status and duration, and the UI exposes the workflow trace. That makes the demonstration explainable and basic failures diagnosable.”

**Technical answer:** `request_log()` sets `X-Request-ID` and logs method/path/status/elapsed milliseconds. Startup logs source/chunk counts; `query()` logs route and graph trace. The browser displays tools, records and warnings. There is no distributed tracing backend, propagated parent correlation through MCP, service-level dashboard or token-cost meter. Request paths contain record identifiers, so logging is not automatically safe for real confidential data.

## 17. What security controls are present?

**Recruiter answer:** “Separate shared keys, read-only enterprise tools, validated inputs and safe UI rendering provide basic demo controls. This is not an enterprise identity or tenant-security implementation.”

**Technical answer:** Key comparison uses `hmac.compare_digest`; Pydantic bounds question length and top-k; tool arguments must match explicit record IDs; SQL values are parameterized; uploaded filenames are metadata basenames; frontend output uses `textContent`; CSP and `nosniff` are applied. Runtime files and private `.env` variants are ignored. There is no OIDC, RBAC, row/document ACL, tenant isolation or per-user audit trail. An application-key holder can also ingest documents; `writes_enabled=False` does not mean the index is immutable.

## 18. How do you address prompt injection?

**Recruiter answer:** “I treat retrieved text as untrusted, keep tool permissions narrow and validate arguments outside the model. I would not rely on a prompt alone for security.”

**Technical answer:** The optional generation prompt tells the model to treat evidence as data, and tool selection cannot name arbitrary tools or record IDs. No enterprise mutations exist. Those controls do not prove resistance to malicious document instructions or prevent data disclosure when access controls are absent. A production design needs authenticated principals, pre-retrieval document authorization, constrained tool scopes, isolated parsing, adversarial tests and monitoring. Never put credentials in model context. A valid citation can still reference malicious or misleading text.

## 19. How are failure and timeout handled?

**Recruiter answer:** “The system avoids inventing operational results, warns on tool failures and can fall back to source evidence when model generation fails.”

**Technical answer:** Each MCP call is bounded by 25 seconds, adapter HTTP by ten seconds, and graph execution by 120 seconds. The semaphore wait happens before that graph deadline, so there is no full request queue deadline. Missing records/tool errors produce warnings; provider errors or bad citation IDs preserve extractive evidence. Generic dependency failures can return 500, and graph timeout returns 504. The health handler is constant after startup, not a comprehensive dependency probe. Retry budgets, circuit breakers and cancellation of synchronous thread work remain production concerns.

## 20. What are the main latency trade-offs?

**Recruiter answer:** “Cold starts, embedding work, model calls and tool process startup all affect response time. The current implementation favors a simple, explainable flow over maximum throughput.”

**Technical answer:** Each tool launches a new Python MCP process and session; calls execute sequentially. The Render profile permits one query at a time and one embedding thread. Model selection plus synthesis adds up to two provider requests for an operational path, subject to retries. I would first measure stage latency and queue time, then consider connection/session reuse, appropriately scoped caching and parallel independent calls. I would not present local regression timing as a hosted production latency SLO.

## 21. How would you scale it?

**Recruiter answer:** “I would separate durable data and ingestion from the web process, add identity-aware access controls and measure the workload before scaling compute.”

**Technical answer:** Local Qdrant storage cannot be shared by extra workers. `QDRANT_URL` and `QDRANT_API_KEY` already select a remote client; this configuration path is tested with a mock, not a live cloud cluster. Horizontal scaling also needs a durable operational backend, source storage, ingestion queue, per-tenant filters, distributed throttling and MCP lifecycle management. Qdrant Cloud alone does not make the whole application stateless or reduce embedding-model memory.

## 22. What does the deployment cost?

**Recruiter answer:** “The initial portfolio deployment uses Render Free with no persistent disk or paid database. It runs semantic retrieval locally and does not require a paid inference API for extractive answers.”

**Technical answer:** `render.yaml` declares one Free Docker service with generated keys and no disk. The model is downloaded during the image build; startup reseeds SQLite and re-indexes repository samples. Free-tier cold starts and usage limits affect availability. Provider calls would introduce token/request charges if enabled. Cost at production scale also includes embedding/re-indexing, operational API traffic, vector storage, observability and reliability. No paid upgrade or current pricing claim is implied by this demo.

## 23. Hosted models versus open-source models?

**Recruiter answer:** “I used a local embedding model for the demo and made hosted generation optional. The choice depends on quality, data boundaries, operations, latency and total cost.”

**Technical answer:** FastEmbed runs the publicly available BGE embedding model locally; that does not mean this repository hosts an open-source generative LLM. Optional generation uses the OpenAI SDK and configured model name. There is no Ollama/vLLM serving stack, GPU service, fine-tuning pipeline or multi-provider abstraction. To add self-hosted generation I would introduce a provider adapter and evaluate quality, licensing, memory/GPU requirements, throughput and security rather than assume a model swap is free or equivalent.

## 24. What happens when the free filesystem disappears?

**Recruiter answer:** “The synthetic demo can rebuild itself from the repository. Temporary uploads are disposable; durable storage can be enabled later.”

**Technical answer:** `lifespan()` calls `seed()`, initializes Qdrant and re-indexes supported sample files before serving traffic. Empty/missing samples fail startup. Stable IDs prevent duplicate sample chunks on retained storage. Seed inserts do not overwrite existing rows, and deleted repository sources are not globally garbage-collected from an existing index. Configure storage paths for an approved volume or select remote Qdrant later. Uploaded originals are not stored; add lasting demo documents to `samples/` or design a source store.

## 25. What would you change before production?

**Recruiter answer:** “I would start with identity, data authorization, durable integration contracts and evaluation evidence. Then I would address throughput and operations based on measured requirements.”

**Technical answer:** Replace shared keys with user/service identity and scoped permissions; enforce document/record access before retrieval/tool execution; isolate uploads and parser work; persist source versions and ingestion jobs; add operational adapter resilience; pool MCP sessions; propagate correlation; set queue deadlines/rate limits; and evaluate answer support and adversarial inputs. Add approved writes only through staged actions tied to an explicit user confirmation and audit record. None of those capabilities should be described as already implemented here.

## A practical interview demonstration

1. Show the deployed UI's semantic/extractive mode and indexed chunks. Keep the workspace key out of screenshots.
2. Ask the P1 policy question, expand `[S1]` and explain `Knowledge.retrieve()`.
3. Ask for ORD-1003 and show `get_order_status` plus `tools:mcp:stdio:enterprise-rest` in the trace.
4. Ask a policy question about TKT-1001 and explain tools-before-retrieval using the returned P1 priority.
5. Show `make_graph()` conditional edges and the tests for citation fallback, explicit record IDs and fresh startup.
6. Close with one honest trade-off: “Fresh MCP sessions and rebuilding a tiny sample index keep this demo understandable. A production workload would need different lifecycle, durability and authorization decisions.”

## Claims to keep precise

| Say | Avoid |
| --- | --- |
| “Deployed synthetic portfolio application” | “Production AI platform used by customers” |
| “Semantic retrieval with inspectable source excerpts” | “Hallucinations eliminated” |
| “Deterministic LangGraph workflow; optional LLM function selection” | “Autonomous agent plans every request” |
| “Real MCP client/server backed by a synthetic REST API” | “Integrated production Salesforce/ServiceNow” |
| “Citation identifier checks and extractive fallback” | “Every generated claim is automatically proven” |
| “14 regression cases, seven acceptance questions, three semantic paraphrases” | “Comprehensively benchmarked answer quality” |
| “Free-tier deployment functionally verified on October 31, 2026” | “Load-tested, highly available or compliance-certified service” |
