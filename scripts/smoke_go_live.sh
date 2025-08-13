#!/usr/bin/env bash
set -euo pipefail
echo "[1/5] Health"
curl -sS http://localhost:8081/api/health || true
curl -sS http://localhost:8081/healthz/full || true

echo "[2/5] SSE stream smoke"
( gtimeout 5 bash -lc "curl -N http://localhost:8081/api/answer-stream/demo & sleep 1; curl -sS -X POST http://localhost:8081/api/meeting-events -H 'Content-Type: application/json' -d '{"action":"caption_chunk","data":{"meetingId":"demo","text":"How would you design multi-region writes?","speaker":"interviewer"}}'; wait" ) || true

echo "[3/5] Approvals"
curl -sS http://localhost:8081/api/approvals || true

echo "[4/5] GitHub webhook (dry)"
curl -sS -X POST http://localhost:8081/webhook/github -H 'X-GitHub-Event: pull_request' -H 'Content-Type: application/json' -d '{"repository":{"full_name":"o/r"},"pull_request":{"number":1}}' || true

echo "[5/5] Jira webhook (dry)"
curl -sS -X POST http://localhost:8081/webhook/jira -H 'Content-Type: application/json' -d '{"issue":{"key":"LAB-1","fields":{"summary":"Test","status":{"name":"In Progress"},"assignee":{"displayName":"You"},"project":{"key":"LAB"}}}}' || true

echo "Done."
