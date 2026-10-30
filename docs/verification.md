# Verification record

## Ephemeral Render revision — October 30, 2026

- Changed the Blueprint to a single Free service with no disk or external datastore. Local configuration checks enforce the free plan, generated secrets, matching loopback port, one-instance/query/thread limits and manual deployment policy.
- All 14 tests passed, including fresh-filesystem rebuild, repeat-startup idempotency, missing-sample startup failure/recovery, configuration-based remote Qdrant selection and MCP subprocess configuration forwarding. Cloud selection uses a mock client, not a live cloud account.
- Rebuilt a fresh local SQLite database and Qdrant index using real semantic embeddings with one embedding thread and one concurrent-query slot. Re-ran the live HTTP/MCP acceptance suite against a separate backend port and enterprise key; current results are in `evaluation-results.json`. Fixed explicit forwarding of API_BASE_URL and ENTERPRISE_API_KEY because the MCP SDK's default subprocess environment does not inherit arbitrary service variables.
- Updated the image to bundle the embedding model during build. Docker/Render builds and actual free-tier memory consumption remain unverified because Docker and a connected Render deployment are not available here.
- No Render resources were created, and nothing was published to GitHub.

## Original implementation checks

Verified locally on Windows with Python 3.14.3 on October 29, 2026.

- Installed application dependencies into `.venv`; `pip check` reports no broken requirements.
- Nine automated tests passed. The suite covers protected APIs, request validation, sample data, policy retrieval, empty-store abstention, real PDF text extraction, source metadata, overlapping chunks, persistent storage, idempotent replacement, operational failures, model citation guards and model tool-argument restrictions.
- Seven live acceptance evaluations passed through the running FastAPI application. Operational queries used the actual stdio MCP client/server and authenticated enterprise REST API, including a missing-record case. The final recorded run used FastEmbed semantic embeddings and extractive generation. See `evaluation-results.json`.
- Three real semantic paraphrase retrieval checks passed using the downloaded BGE ONNX embedding model. See `semantic-evaluation-results.json`.
- Inspected the browser UI, connected with the local development key, executed the combined ticket/policy query, and expanded its MCP trace. `demo-proof.png` records the visible citations and trace.
- Checked pinned non-Windows dependencies for availability of Linux x86_64 Python 3.12 wheels. This is not a Docker build or a Linux runtime test.

## Outstanding external verification

- No OpenAI API key was supplied. Function-selection and citation-checking code paths have mock-based tests; live provider generation and function calling remain unverified. Set `OPENAI_API_KEY` in the ignored `.env` or a deployment secret store, then run the acceptance evaluation again. Never paste a secret into a Git-tracked file or issue.
- Docker is not installed on this workstation. The image/Compose definitions have not been built here. Linux CI is configured but has not run remotely from this local working tree.
- Render is now the selected host. The initial profile is Free compute with ephemeral storage, no persistent disk and automatic sample rebuilding. It has not been deployed to a public URL. Repository publication and a connected Render account are still needed; actual free-tier memory/build/runtime verification remains outstanding.
- Qdrant Cloud configuration is implemented but was not exercised against a live cluster.

The checks are small portfolio regression tests. They do not establish production readiness, exhaustive security coverage, or elimination of unsupported model claims.
