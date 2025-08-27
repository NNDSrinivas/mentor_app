import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app_factory import create_app
from backend import middleware


def test_meeting_events_rate_limiting():
    app = create_app()
    client = app.test_client()
    # lower rate limit for test
    middleware.BUCKETS.rates['MEETING_EVENTS_PER_MIN'] = 2
    # first three requests pass (initial bucket creation grants full tokens)
    assert client.post('/api/meeting-events', json={}).status_code == 200
    assert client.post('/api/meeting-events', json={}).status_code == 200
    assert client.post('/api/meeting-events', json={}).status_code == 200
    # fourth request should be rate limited
    res = client.post('/api/meeting-events', json={})
    assert res.status_code == 429
