"""Download the real embedding model and check semantic retrieval on paraphrases."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.knowledge import Knowledge


def main():
    kb = Knowledge(Settings(embedding_mode='fastembed', qdrant_path='data/semantic-evaluation', qdrant_url=None))
    results = []
    try:
        for path in Path('samples').glob('*.md'):
            kb.ingest(path.name, path.read_bytes())
        for question, expected in [
            ('Who must be notified when production goes down?', 'escalation.md'),
            ('Can we get our money back for an enterprise subscription?', 'refunds.md'),
            ('How do administrators restore access safely?', 'accounts.md')]:
            hits = kb.retrieve(question, 3)
            passed = bool(hits) and hits[0].source == expected
            results.append({'question':question,'expected':expected,'top_source':hits[0].source if hits else None,
                            'passed':passed, 'scores':[h.score for h in hits]})
            print('PASS' if passed else 'FAIL', question, results[-1]['top_source'])
    finally:
        kb.client.close()
    Path('docs/semantic-evaluation-results.json').write_text(json.dumps(results,indent=2)+'\n')
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
