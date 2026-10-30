import hashlib
import math
import re
import threading
import uuid
from pathlib import Path
from pypdf import PdfReader
from qdrant_client import QdrantClient, models
from app.models import Citation


class Knowledge:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.RLock()
        if cfg.embedding_mode not in ('offline', 'fastembed'):
            raise ValueError('EMBEDDING_MODE must be offline or fastembed')
        self.encoder = None
        self.dimension = 384
        if cfg.embedding_mode == 'fastembed':
            import os
            import sys
            # Virtual environments on Windows do not always search Scripts for the
            # app-local MSVC DLLs installed by the msvc-runtime wheel.
            if sys.platform == 'win32':
                self._dll_directory = os.add_dll_directory(str(Path(sys.executable).parent))
            from fastembed import TextEmbedding
            self.encoder = TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir=cfg.model_cache_path,
                                         threads=cfg.embedding_threads)
        self.client = (QdrantClient(url=cfg.qdrant_url, api_key=cfg.qdrant_api_key, timeout=15)
                       if cfg.qdrant_url else QdrantClient(path=cfg.qdrant_path))
        self.collection = 'knowledge_' + cfg.embedding_mode + '_v1'
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(
                size=self.dimension, distance=models.Distance.COSINE))

    def embed(self, texts):
        if self.encoder:
            return [v.tolist() for v in self.encoder.embed(texts)]
        # Reproducible normalized feature hashing: offline lexical baseline, NOT semantic embeddings.
        vectors = []
        for text in texts:
            v = [0.0] * self.dimension
            for token in re.findall(r'[a-z0-9]+', text.lower()):
                h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
                v[h % self.dimension] += 1 if h & 512 else -1
            norm = math.sqrt(sum(x*x for x in v)) or 1
            vectors.append([x/norm for x in v])
        return vectors

    def ingest(self, name: str, content: bytes):
        import io
        suffix = Path(name).suffix.lower()
        if suffix == '.pdf':
            reader = PdfReader(io.BytesIO(content))
            if len(reader.pages) > 200:
                raise ValueError('Maximum 200 PDF pages')
            pages = [(i+1, p.extract_text() or '') for i, p in enumerate(reader.pages)]
        elif suffix in ('.txt', '.md'):
            pages = [(1, content.decode('utf-8'))]
        else:
            raise ValueError('Supported formats: PDF, TXT, MD')
        points = []
        for page, text in pages:
            words = text.split()
            for start in range(0, len(words), 180):
                chunk = ' '.join(words[start:start+220])
                if not chunk.strip():
                    continue
                index = start // 180
                payload = dict(source=name, page=page, chunk=index, text=chunk)
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'{name}:{page}:{index}'))
                points.append((point_id, payload))
        if not points:
            raise ValueError('No extractable text; scanned PDFs require OCR before ingestion')
        vectors = self.embed([p[1]['text'] for p in points])
        with self.lock:
            # Serialize replacement with queries; full parse/embedding succeeds before replacement.
            self.client.delete(self.collection, models.FilterSelector(filter=models.Filter(must=[
                models.FieldCondition(key='source', match=models.MatchValue(value=name))])), wait=True)
            for offset in range(0, len(points), 64):
                self.client.upsert(self.collection, points=[models.PointStruct(id=i, vector=v, payload=p)
                    for (i,p),v in zip(points[offset:offset+64], vectors[offset:offset+64])], wait=True)
        return len(points)

    def retrieve(self, question, top_k):
        vector = self.embed([question])[0]
        with self.lock:
            hits = self.client.query_points(self.collection, query=vector, limit=top_k,
                                            score_threshold=0.20).points
        return [Citation(id=f'S{i+1}', score=float(h.score), **h.payload) for i,h in enumerate(hits)]

    def count(self):
        with self.lock:
            return self.client.count(self.collection, exact=True).count
