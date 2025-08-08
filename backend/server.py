# backend/server.py
import asyncio, json, os, logging, hmac, hashlib
import websockets
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Set
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Import functions to avoid circular imports
def get_backend_components():
    from backend.approvals import approvals
    from backend.approval_worker import on_approval_resolved, start_worker_thread, set_dry_run_mode, get_integration_status
    from backend.watchers.ci_watcher import handle_github_webhook
    return approvals, on_approval_resolved, start_worker_thread, set_dry_run_mode, get_integration_status, handle_github_webhook

approvals, on_approval_resolved, start_worker_thread, set_dry_run_mode, get_integration_status, handle_github_webhook = get_backend_components()

# Start the approval worker thread
start_worker_thread()

# WebSocket connections for real-time notifications
connected_clients: Set[websockets.WebSocketServerProtocol] = set()

# GitHub webhook secret for verification
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not API_AUTH_TOKEN:
            return func(*args, **kwargs)
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
        if hmac.compare_digest(token, API_AUTH_TOKEN):
            return func(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401

    return wrapper

# --- Health Check ---
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    status = get_integration_status()
    return jsonify({
        'status': 'healthy',
        'timestamp': asyncio.get_event_loop().time(),
        'integrations': status
    })

# --- Approvals REST API ---
@app.route("/api/approvals", methods=['GET'])
@require_auth
def list_approvals():
    """List all pending approvals"""
    try:
        items = approvals.list()
        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        log.error(f"Error listing approvals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/approvals/<approval_id>", methods=['GET'])
@require_auth
def get_approval(approval_id: str):
    """Get specific approval details"""
    try:
        item = approvals.get(approval_id)
        if not item:
            return jsonify({"error": "Approval not found"}), 404
        return jsonify(vars(item))
    except Exception as e:
        log.error(f"Error getting approval {approval_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/approvals/resolve", methods=['POST'])
@require_auth
def resolve_approval():
    """Resolve (approve/reject) an approval request"""
    try:
        data = request.get_json(force=True)
        item_id = data.get("id")
        decision = data.get("decision")  # approve|reject
        result_data = data.get("result", {})
        
        if not item_id or decision not in ["approve", "reject"]:
            return jsonify({"error": "Invalid request"}), 400
        
        # Resolve the approval
        resolved_item = approvals.resolve(item_id, decision, result=result_data)
        
        # Execute if approved
        exec_result = on_approval_resolved(resolved_item)
        resolved_item["exec_result"] = exec_result
        
        # Notify WebSocket clients
        notify_all({
            "type": "approval_resolved",
            "approval": resolved_item,
            "decision": decision
        })
        
        log.info(f"Approval {item_id} {decision}d: {resolved_item.get('action')}")
        return jsonify(resolved_item)
        
    except Exception as e:
        log.error(f"Error resolving approval: {e}")
        return jsonify({"error": str(e)}), 500

# --- GitHub Integration Endpoints ---
@app.route("/api/github/pr", methods=['POST'])
@require_auth
def github_pr():
    """Submit GitHub PR creation for approval"""
    try:
        data = request.get_json(force=True)
        required_fields = ["owner", "repo", "head", "base", "title"]
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields", "required": required_fields}), 400
        
        item = approvals.submit("github.pr", data)
        
        # Notify WebSocket clients
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        log.error(f"Error submitting GitHub PR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/github/comment", methods=['POST'])
@require_auth
def github_comment():
    """Submit GitHub comment for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("github.comment", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/github/issue", methods=['POST'])
@require_auth
def github_issue():
    """Submit GitHub issue creation for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("github.issue", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Jira Integration Endpoints ---
@app.route("/api/jira/create", methods=['POST'])
@require_auth
def jira_create():
    """Submit Jira issue creation for approval"""
    try:
        data = request.get_json(force=True)
        required_fields = ["project_key", "summary", "description"]
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields", "required": required_fields}), 400
        
        item = approvals.submit("jira.create", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/jira/update", methods=['POST'])
@require_auth
def jira_update():
    """Submit Jira issue update for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("jira.update", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/jira/comment", methods=['POST'])
@require_auth
def jira_comment():
    """Submit Jira comment for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("jira.comment", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GitHub Webhook for CI/status events ---
@app.route("/webhook/github", methods=['POST'])
def gh_webhook():
    """Handle GitHub webhooks"""
    try:
        # Verify webhook signature if secret is configured
        if GITHUB_WEBHOOK_SECRET:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not verify_github_signature(request.data, signature):
                log.warning("Invalid GitHub webhook signature")
                return "Invalid signature", 401
        
        event = request.headers.get("X-GitHub-Event", "unknown")
        payload = request.get_json(force=True) or {}
        
        log.info(f"Received GitHub webhook: {event}")
        
        # Handle the webhook event
        handle_github_webhook(event, payload)
        
        # Notify WebSocket clients about the event
        notify_all({
            "type": "webhook_received",
            "event": event,
            "repository": payload.get("repository", {}).get("full_name", "unknown")
        })
        
        return "", 204
    except Exception as e:
        log.error(f"Error handling GitHub webhook: {e}")
        return "Internal error", 500

def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    provided_signature = signature_header[7:]  # Remove 'sha256=' prefix
    return hmac.compare_digest(expected_signature, provided_signature)

# --- Wave 6 PR Auto-Reply Webhook ---
@app.route("/webhook/github/pr", methods=['POST'])
def gh_pr_webhook():
    """Handle GitHub PR webhooks for auto-reply suggestions"""
    try:
        # Import Wave 6 components
        from integrations.github_fetch import get_pr, get_pr_files, get_pr_comments
        from pr_auto_reply import suggest_replies_and_patch
        
        event = request.headers.get("X-GitHub-Event", "unknown")
        payload = request.get_json(force=True) or {}
        
        if event not in ("pull_request", "issue_comment"): 
            return "", 204

        repo_full = payload.get("repository",{}).get("full_name","")
        owner, repo = repo_full.split("/") if "/" in repo_full else ("","")
        pr_number = (payload.get("pull_request") or {}).get("number") or payload.get("issue",{}).get("number")

        if not (owner and repo and pr_number):
            return "", 204

        pr = get_pr(owner, repo, pr_number)
        files = get_pr_files(owner, repo, pr_number)
        comments = get_pr_comments(owner, repo, pr_number)

        suggestions = suggest_replies_and_patch(pr.get("title",""), pr.get("body","") or "", files, comments)
        
        # Gate via approvals before posting anything
        item = approvals.submit("github.pr_auto_reply", {
            "owner": owner, 
            "repo": repo, 
            "pr_number": pr_number, 
            "suggestions_json": suggestions["raw"]
        })
        
        # Notify WebSocket clients
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })
        
        return "", 204
    except Exception as e:
        log.error(f"Error handling PR webhook: {e}")
        return "", 500

# --- Wave 6 Documentation API ---
@app.route("/api/docs/adr", methods=['POST'])
@require_auth
def api_draft_adr():
    """Generate ADR (Architecture Decision Record)"""
    try:
        from doc_agent import draft_adr
        d = request.get_json(force=True)
        md = draft_adr(d["title"], d.get("context",""), d.get("options",[]), d.get("decision",""), d.get("consequences",[]))
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting ADR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/docs/runbook", methods=['POST'])
@require_auth
def api_draft_runbook():
    """Generate operational runbook"""
    try:
        from doc_agent import draft_runbook
        d = request.get_json(force=True)
        md = draft_runbook(d["service"], d.get("incidents",[]), d.get("commands",[]), d.get("dashboards",[]))
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting runbook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/docs/changelog", methods=['POST'])
@require_auth
def api_draft_changelog():
    """Generate changelog from merged PRs"""
    try:
        from doc_agent import draft_changelog
        d = request.get_json(force=True)
        md = draft_changelog(d["repo"], d.get("merged_prs",[]))
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting changelog: {e}")
        return jsonify({"error": str(e)}), 500

# --- Wave 7 Mobile Relay Endpoint ---
@app.route("/api/relay/mobile", methods=['POST'])
@require_auth
def relay_mobile():
    """Relay messages to mobile WebSocket clients during stealth mode"""
    try:
        payload = request.get_json(force=True) or {}
        # broadcast to mobile WS clients
        notify_all({
            "channel": "mobile",
            "type": payload.get("type", "answer"), 
            "text": payload.get("text", ""),
            "meetingId": payload.get("meetingId", "")
        })
        return jsonify({"ok": True})
    except Exception as e:
        log.error(f"Error relaying to mobile: {e}")
        return jsonify({"error": str(e)}), 500

# --- Configuration Endpoints ---
@app.route("/api/config/dry-run", methods=['POST'])
@require_auth
def set_dry_run():
    """Enable/disable dry run mode"""
    try:
        data = request.get_json(force=True)
        enabled = data.get("enabled", True)
        set_dry_run_mode(enabled)
        
        return jsonify({
            "dry_run_enabled": enabled,
            "message": f"Dry run mode {'enabled' if enabled else 'disabled'}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/config/status", methods=['GET'])
@require_auth
def config_status():
    """Get current configuration status"""
    try:
        return jsonify(get_integration_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- WebSocket Support ---
async def ws_handler(websocket):
    """Handle WebSocket connections"""
    connected_clients.add(websocket)
    log.info(f"WebSocket client connected. Total: {len(connected_clients)}")
    
    try:
        # Send current pending approvals to new client
        pending = approvals.list()
        if pending:
            await websocket.send(json.dumps({
                "type": "pending_approvals",
                "approvals": pending
            }))
        
        # Keep connection alive
        async for message in websocket:
            # Echo back or handle client messages if needed
            data = json.loads(message)
            log.debug(f"Received WebSocket message: {data}")
            
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        log.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")

async def ws_server():
    """Start WebSocket server"""
    port = int(os.getenv("WS_PORT", "8001"))
    log.info(f"Starting WebSocket server on port {port}")
    async with websockets.serve(ws_handler, "0.0.0.0", port):
        await asyncio.Future()  # Run forever

def notify_all(message: dict):
    """Send message to all WebSocket clients"""
    if not connected_clients:
        return
    
    message_text = json.dumps(message)
    asyncio.create_task(_broadcast(message_text))

async def _broadcast(message_text: str):
    """Broadcast message to all connected clients"""
    if not connected_clients:
        return
    
    dead_connections = []
    for websocket in connected_clients:
        try:
            await websocket.send(message_text)
        except Exception as e:
            log.debug(f"Failed to send to WebSocket client: {e}")
            dead_connections.append(websocket)
    
    # Remove dead connections
    for websocket in dead_connections:
        connected_clients.discard(websocket)

# --- Server Startup ---
def run_flask_server():
    """Run Flask server"""
    port = int(os.getenv("FLASK_PORT", "8081"))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    log.info(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)

def run_servers():
    """Run both Flask and WebSocket servers"""
    import threading
    
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Run WebSocket server in main thread
    try:
        asyncio.run(ws_server())
    except KeyboardInterrupt:
        log.info("Shutting down servers...")

if __name__ == "__main__":
    # Check for dry run mode from environment
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    set_dry_run_mode(dry_run)
    
    log.info(f"Starting Wave 5 servers (dry_run={dry_run})")
    run_servers()
