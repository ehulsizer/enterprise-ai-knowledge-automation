# Render deployment: free, disposable portfolio demo

`render.yaml` defines one **Free Docker web service**, one instance, no persistent disk and no managed database. No paid resources are declared or have been created. Semantic retrieval uses the local BGE ONNX model and Qdrant local mode; generation is extractive unless an optional provider key is added.

Render's free service has an ephemeral filesystem: local changes are lost on restart, redeploy or spin-down. It sleeps after 15 minutes without inbound traffic and has workspace usage limits. See [Render's free-service limits](https://render.com/docs/free). This is a demo configuration, not a production deployment.

## Rebuild on startup

Before FastAPI becomes ready, startup creates missing SQLite tables and inserts missing synthetic customers, orders and tickets. It opens/creates the configured Qdrant collection, then parses, chunks, embeds and re-indexes all supported documents directly in the repository's `samples/` directory. Markdown, UTF-8 text and text-based PDFs are supported. Stable source/chunk IDs and replacement of each sample's previous chunks prevent duplication. Missing/empty samples or indexing failure fails startup instead of advertising an empty healthy demo.

The Docker build downloads the public embedding model into `/app/data/models` in the image. A fresh instance starts with those baked-in files and rebuilds vectors from repository documents. A missing model cache can still download at runtime. Model weights are not committed to Git. Builds need outbound internet access.

UI-uploaded documents are temporary: their source bytes are not saved, and their local vectors disappear when the filesystem resets. To retain a demo policy, commit its source to `samples/` and publish/redeploy. No runtime database files need to be committed or backed up for this synthetic demo. If files survive a restart, missing seed rows are restored and samples refreshed without discarding other existing sources.

## Publish and deploy

1. Review, commit and push the implementation, including the Blueprint, Dockerfile and samples, to `ehulsizer/enterprise-ai-knowledge-automation` on `main`. Local files are not visible to Render until published.
2. Install/connect the Render integration or sign in to its dashboard. Authorize access to this GitHub repository. Create a Blueprint and verify **Free**, **no disk**, and **no additional datastore** before applying. Do not select a paid upgrade.
3. Render generates independent `APP_API_KEY` and `ENTERPRISE_API_KEY`. Retrieve the application key in Environment settings and enter it in the UI workspace field; keep the enterprise key private. Do not use the local defaults publicly.
4. Leave `OPENAI_API_KEY` unset for the initial demo. Semantic retrieval, MCP and extractive answers work without inference charges. Add it later only through Render's secret settings if live generation is desired; provider usage may cost money.
5. Wait for image build and startup. Port 8000, loopback MCP-to-REST routing and `/health` are configured. Automatic deploys are off; later pushes require manual deploys.
6. Verify `/health`, authenticated `/api/status`, a policy query, ORD-1003 and the combined TKT-1001 query on the public URL. Restart and repeat to verify rebuilding. Expect cold starts after idle periods.

## Requirements and future storage

The free profile uses one embedding thread, one chat query at a time and one Uvicorn worker to reduce memory pressure while retaining semantic retrieval. Actual Linux/Render memory use, build, cold-start time and MCP execution still need public runtime verification. If the free instance cannot run reliably, report the evidence before proposing a paid change. `EMBEDDING_MODE=offline` remains an explicit lower-resource lexical fallback, not semantic retrieval.

No redesign is needed for later storage choices:

- Qdrant Cloud: set `QDRANT_URL` and `QDRANT_API_KEY`. The existing vector client selects the remote backend; re-ingest custom sources into a new collection. Embeddings still run locally.
- Persistent filesystem: after separate approval of charges, mount storage and point `QDRANT_PATH`, `ENTERPRISE_DB_PATH` and `MODEL_CACHE_PATH` at it. Keep one worker for Qdrant local mode.
- `SAMPLE_DOCUMENTS_PATH` can select another repository-managed source directory; the default is `samples`.

This remains a shared-key, single-tenant synthetic demo. The Blueprint is checked locally, not applied to Render. See [Blueprint specification](https://render.com/docs/blueprint-spec) and [storage options](https://render.com/docs/disks).
