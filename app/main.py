import asyncio
import hmac
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from app.config import settings
from app.enterprise import router, seed
from app.knowledge import Knowledge
from app.models import Answer, Query
from app.workflow import make_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('platform')


@asynccontextmanager
async def lifespan(app):
    cfg = settings()
    await asyncio.to_thread(seed)
    kb = await asyncio.to_thread(Knowledge, cfg)
    try:
        samples = sorted(p for p in Path(cfg.sample_documents_path).iterdir()
                         if p.is_file() and p.suffix.lower() in ('.md', '.txt', '.pdf'))
        if not samples:
            raise ValueError('Startup requires at least one repository-managed sample document')
        for path in samples:
            chunks = await asyncio.to_thread(kb.ingest, path.name, path.read_bytes())
            log.info('startup_sample source=%s chunks=%s', path.name, chunks)
        app.state.kb = kb
        app.state.graph = make_graph(kb)
        app.state.query_slots = asyncio.Semaphore(cfg.max_concurrent_queries)
        yield
    finally:
        kb.client.close()


app = FastAPI(title='Enterprise AI Knowledge & Automation', version='1.0.0', lifespan=lifespan)


def auth(x_api_key: str = Header(default='')):
    if not hmac.compare_digest(x_api_key, settings().app_api_key):
        raise HTTPException(401, 'Valid X-API-Key required')


def enterprise_auth(x_enterprise_key: str = Header(default='')):
    if not hmac.compare_digest(x_enterprise_key, settings().enterprise_api_key):
        raise HTTPException(401, 'Valid X-Enterprise-Key required')


app.include_router(router, dependencies=[Depends(enterprise_auth)])


@app.middleware('http')
async def request_log(request: Request, call_next):
    request_id, start = uuid.uuid4().hex, time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception('request_failed id=%s', request_id)
        response = JSONResponse(status_code=500, content={'detail': 'Internal error', 'request_id': request_id})
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.url.path in ('/docs', '/redoc'):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
    else:
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'"
    log.info('request id=%s method=%s path=%s status=%s duration_ms=%.1f', request_id,
             request.method, request.url.path, response.status_code, (time.perf_counter()-start)*1000)
    return response


@app.get('/', include_in_schema=False)
def index():
    return FileResponse('app/static/index.html')


@app.get('/assets/{filename}', include_in_schema=False)
def asset(filename: str):
    if filename not in ('app.js', 'style.css'):
        raise HTTPException(404)
    return FileResponse(Path('app/static') / filename)


@app.get('/health')
def health():
    return {'status': 'ok', 'synthetic_data': True}


@app.get('/api/status', dependencies=[Depends(auth)])
def status(request: Request):
    return {'chunks': request.app.state.kb.count(), 'embedding_mode': settings().embedding_mode,
            'generation_mode': 'openai' if settings().openai_api_key else 'extractive', 'writes_enabled': False}


@app.post('/api/query', response_model=Answer, dependencies=[Depends(auth)])
async def query(body: Query, request: Request):
    async with request.app.state.query_slots:
        try:
            result = await asyncio.wait_for(request.app.state.graph.ainvoke(body.model_dump(), {'recursion_limit': 10}), timeout=120)
        except TimeoutError:
            raise HTTPException(504, 'Query timed out; retry with a narrower request')
    log.info('workflow route=%s trace=%s', result['route'], result['trace'])
    return Answer(**{k:v for k,v in result.items() if k not in ('question','top_k')},
        embedding_mode=settings().embedding_mode)


@app.post('/api/ingest', dependencies=[Depends(auth)])
async def ingest(request: Request, file: UploadFile = File(...)):
    content = await file.read(5*1024*1024 + 1)
    if len(content) > 5*1024*1024:
        raise HTTPException(413, 'Maximum file size is 5 MiB')
    name = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    if not name or len(name) > 150:
        raise HTTPException(422, 'Invalid source filename')
    try:
        chunks = await asyncio.to_thread(request.app.state.kb.ingest, name, content)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        log.exception('ingestion_failed')
        raise HTTPException(422, 'Document could not be parsed or indexed')
    return {'source': name, 'chunks': chunks}
