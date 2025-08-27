import os
import sys
from pathlib import Path

# Ensure repo root on path for local imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app_factory import create_app


def test_healthz_full(tmp_path):
    os.environ['OPENAI_API_KEY'] = 'test'
    os.environ['GITHUB_WEBHOOK_SECRET'] = 'gh'
    os.environ['JIRA_WEBHOOK_SECRET'] = 'jira'
    app = create_app()
    client = app.test_client()
    res = client.get('/healthz/full')
    assert res.status_code == 200
    data = res.get_json()
    assert data['checks']['OPENAI_API_KEY'] is True
    assert data['checks']['VECTOR_DB_PATH_EXISTS'] is True
    assert data['checks']['GITHUB_WEBHOOK_SECRET'] is True
    assert data['checks']['JIRA_WEBHOOK_SECRET'] is True
