import os
import sys

# Ensure project root is on sys.path so we can import backend.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import backend


def run():
    print('Endpoint smoke test starting...')

    try:
        client = backend.app.test_client()
        r = client.get('/health')
        print('GET /health:', r.status_code, r.json)

        r2 = client.get('/liblouis/tables')
        tables = (r2.json or {}).get('tables', [])
        print('GET /liblouis/tables:', r2.status_code, 'tables:', len(tables))
    except Exception as e:
        print('Endpoints FAIL:', e)

    print('Endpoint smoke test done.')


if __name__ == '__main__':
    run()
