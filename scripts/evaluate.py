"""Live acceptance evaluation; starts real stdio MCP subprocesses through the API."""
import json
import os
import time
from pathlib import Path
import httpx

CASES = [
    ('What is the escalation policy for a priority-one support incident?', 'knowledge', '15 minutes'),
    ('What does the refund policy say about enterprise subscriptions?', 'knowledge', '30'),
    ('What is the status of order ORD-1003?', 'operational', 'in transit'),
    ('Show the open service tickets for customer CUST-002.', 'operational', 'TKT-1001'),
    ('According to policy, what should happen next for ticket TKT-1001?', 'both', '15 minutes'),
    ('hello assistant', 'clarify', 'Ask about'),
    ('What is the status of order ORD-9999?', 'operational', 'No operational data'),
]


def main():
    results = []
    with httpx.Client(base_url=os.getenv('API_BASE_URL','http://127.0.0.1:8000'), timeout=150,
        headers={'X-API-Key':os.getenv('APP_API_KEY','local-demo-key-change-before-hosting')}) as client:
        for question, route, expected in CASES:
            start = time.perf_counter()
            r = client.post('/api/query', json={'question':question})
            r.raise_for_status()
            data = r.json()
            checks = {'route':data['route']==route, 'answer_contains':expected.lower() in data['answer'].lower(),
                      'citations_present':bool(data['citations']) if route in ('knowledge','both') else True,
                      'mcp_used':bool(data['tools']) if route in ('operational','both') and '9999' not in question else True}
            results.append({'question':question,'checks':checks,'passed':all(checks.values()),'trace':data['trace'],
                            'embedding_mode':data['embedding_mode'],'generation_mode':data['generation_mode'],
                            'duration_ms':round((time.perf_counter()-start)*1000,1)})
            print(('PASS' if all(checks.values()) else 'FAIL'), question, checks)
    Path('docs').mkdir(exist_ok=True)
    Path('docs/evaluation-results.json').write_text(json.dumps(results,indent=2)+'\n')
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
