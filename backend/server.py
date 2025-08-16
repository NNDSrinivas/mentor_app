# backend/server.py
import asyncio, json, os, logging, hmac, hashlib
import websockets
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Set
from backend.integrations.github_manager import GitHubManager
from backend.memory_service import MemoryService
from app.task_manager import Task, TaskManager

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ship-It PR: Add healthz blueprint
from backend.healthz import bp as healthz_bp
app.register_blueprint(healthz_bp)

# Ship-It PR: Add middleware for rate limiting and cost tracking
from backend.middleware import rate_limit, record_cost
from backend.audit import audit
from backend.webhook_signatures import verify_github, verify_jira
from backend.payments import subscription_required, handle_webhook as handle_stripe_webhook

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
from typing import Any as _Any
connected_clients: Set[_Any] = set()

# Task manager instance for task operations
task_manager = TaskManager()
memory_service = MemoryService()

# GitHub webhook secret for verification
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

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
@subscription_required
def list_approvals():
    """List all pending approvals"""
    try:
        items = approvals.list()
        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        log.error(f"Error listing approvals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/approvals/<approval_id>", methods=['GET'])
@subscription_required
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
@subscription_required
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
        audit("approval_resolve", {"id": item_id, "decision": decision})
        return jsonify(resolved_item)
        
    except Exception as e:
        log.error(f"Error resolving approval: {e}")
        return jsonify({"error": str(e)}), 500

# --- GitHub Integration Endpoints ---
@app.route("/api/github/pr", methods=['POST'])
@subscription_required
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

        audit("github_pr_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        log.error(f"Error submitting GitHub PR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/github/comment", methods=['POST'])
@subscription_required
def github_comment():
    """Submit GitHub comment for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("github.comment", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })

        audit("github_comment_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/github/issue", methods=['POST'])
@subscription_required
def github_issue():
    """Submit GitHub issue creation for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("github.issue", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })

        audit("github_issue_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Jira Integration Endpoints ---
@app.route("/api/jira/create", methods=['POST'])
@subscription_required
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

        audit("jira_create_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/jira/update", methods=['POST'])
@subscription_required
def jira_update():
    """Submit Jira issue update for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("jira.update", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })

        audit("jira_update_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/jira/comment", methods=['POST'])
@subscription_required
def jira_comment():
    """Submit Jira comment for approval"""
    try:
        data = request.get_json(force=True)
        item = approvals.submit("jira.comment", data)
        
        notify_all({
            "type": "new_approval",
            "approval": vars(item)
        })

        audit("jira_comment_submit", {"approval_id": item.id})
        return jsonify({"submitted": True, "approvalId": item.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Code Generation Endpoint ---
@app.route("/api/codegen", methods=["POST"])
@subscription_required
def codegen():
    """Generate code for a task and open a PR"""
    try:
        data = request.get_json(force=True)
        required_fields = ["task_id", "title", "description", "files"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields", "required": required_fields}), 400

        task = Task(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            status=data.get("status", "in_progress"),
            assignee=data.get("assignee"),
        )
        task_manager.active_tasks[task.task_id] = task

        files = data["files"]
        base_branch = data.get("base_branch", "main")
        branch_name = data.get("branch", f"task-{task.task_id}")

        repo_full = data.get("repo") or os.getenv("GITHUB_REPO", "")
        if "/" in repo_full:
            owner, repo = repo_full.split("/", 1)
        else:
            owner, repo = repo_full, ""

        gh = GitHubManager(dry_run=os.getenv("GITHUB_DRY_RUN", "true").lower() == "true")

        gh.create_branch(owner, repo, base_branch, branch_name)
        for path, content in files.items():
            gh.commit_file(owner, repo, branch_name, path, content.encode("utf-8"), f"Add {path} for {task.title}")
        pr = gh.create_pr(owner, repo, head=branch_name, base=base_branch, title=data.get("pr_title", task.title), body=data.get("pr_body", task.description))

        pr_number = pr.get("number")
        status = gh.get_pr(owner, repo, pr_number) if pr_number else pr
        comments = gh.get_pr_comments(owner, repo, pr_number) if pr_number else {"comments": []}

        # Update JIRA task status and comment
        try:
            task_manager.jira.update_task_status(task.task_id, "review")
            pr_url = pr.get("html_url", "")
            if pr_url:
                task_manager.jira.add_comment(task.task_id, f"PR created: {pr_url}")
        except Exception as jira_err:
            log.debug(f"JIRA update failed: {jira_err}")

        notify_all({
            "type": "codegen_pr",
            "task_id": task.task_id,
            "pr": pr,
            "status": status,
            "comments": comments,
        })

        audit("codegen_pr", {"task_id": task.task_id, "pr_number": pr.get("number")})
        return jsonify({"pr": pr, "status": status, "comments": comments})
    except Exception as e:
        log.error(f"Error generating code: {e}")
        return jsonify({"error": str(e)}), 500

# --- GitHub Webhook for CI/status events ---
@app.route("/webhook/github", methods=['POST'])
def gh_webhook():
    """Handle GitHub webhooks"""
    try:
        # Ship-It PR: Use new webhook signature verification
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = request.get_data()
        if not verify_github(signature, body):
            log.warning("Invalid GitHub webhook signature")
            return "", 401
        
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

        audit("github_webhook", {"event": event})
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

# --- Stripe Webhook ---
@app.route("/webhook/stripe", methods=['POST'])
def stripe_webhook():
    """Handle Stripe subscription and invoice webhooks"""
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        handle_stripe_webhook(payload, sig)
        audit("stripe_webhook", {})
    except Exception as e:
        log.error(f"Error handling Stripe webhook: {e}")
        return "", 400
    return "", 204

# --- Wave 6 PR Auto-Reply Webhook ---
@app.route("/webhook/github/pr", methods=['POST'])
def gh_pr_webhook():
    """Handle GitHub PR webhooks for auto-reply suggestions"""
    try:
        # Ship-It PR: Add webhook signature verification
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = request.get_data()
        if not verify_github(signature, body):
            return "", 401
            
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

        suggestions = suggest_replies_and_patch(
            pr.get("title", ""),
            pr.get("body", "") or "",
            files,
            comments,
            owner,
            repo,
            pr_number,
        )
        
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

        audit("github_pr_webhook", {"event": event, "pr_number": pr_number})
        return "", 204
    except Exception as e:
        log.error(f"Error handling PR webhook: {e}")
        return "", 500

# --- Wave 6 Documentation API ---
@app.route("/api/docs/adr", methods=['POST'])
@subscription_required
def api_draft_adr():
    """Generate ADR (Architecture Decision Record)"""
    try:
        # Use explicit package path for editor/type checker compatibility
        from backend.doc_agent import draft_adr
    except RuntimeError as e:
        log.error(f"Doc agent initialization error: {e}")
        return jsonify({"error": str(e)}), 500
    try:
        d = request.get_json(force=True)
        md = draft_adr(d["title"], d.get("context",""), d.get("options",[]), d.get("decision",""), d.get("consequences",[]))
        audit("draft_adr", {"title": d.get("title")})
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting ADR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/docs/runbook", methods=['POST'])
@subscription_required
def api_draft_runbook():
    """Generate operational runbook"""
    try:
        from backend.doc_agent import draft_runbook
    except RuntimeError as e:
        log.error(f"Doc agent initialization error: {e}")
        return jsonify({"error": str(e)}), 500
    try:
        d = request.get_json(force=True)
        md = draft_runbook(d["service"], d.get("incidents",[]), d.get("commands",[]), d.get("dashboards",[]))
        audit("draft_runbook", {"service": d.get("service")})
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting runbook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/docs/changelog", methods=['POST'])
@subscription_required
def api_draft_changelog():
    """Generate changelog from merged PRs"""
    try:
        from backend.doc_agent import draft_changelog
    except RuntimeError as e:
        log.error(f"Doc agent initialization error: {e}")
        return jsonify({"error": str(e)}), 500
    try:
        d = request.get_json(force=True)
        md = draft_changelog(d["repo"], d.get("merged_prs",[]))
        audit("draft_changelog", {"repo": d.get("repo")})
        return jsonify({"markdown": md})
    except Exception as e:
        log.error(f"Error drafting changelog: {e}")
        return jsonify({"error": str(e)}), 500

# --- Wave 7 Mobile Relay Endpoint ---
@app.route("/api/relay/mobile", methods=['POST'])
@subscription_required
@rate_limit('meeting')
def relay_mobile():
    """Relay messages to mobile WebSocket clients during stealth mode"""
    try:
        payload = request.get_json(force=True) or {}
        # Ship-It PR: Record cost for mobile relay
        record_cost(tokens=100)  # Estimate for mobile relay
        
        # broadcast to mobile WS clients
        notify_all({
            "channel": "mobile",
            "type": payload.get("type", "answer"),
            "text": payload.get("text", ""),
            "meetingId": payload.get("meetingId", "")
        })
        audit("relay_mobile", {"meetingId": payload.get("meetingId", "")})
        return jsonify({"ok": True})
    except Exception as e:
        log.error(f"Error relaying to mobile: {e}")
        return jsonify({"error": str(e)}), 500

# --- Configuration Endpoints ---
@app.route("/api/config/dry-run", methods=['POST'])
def set_dry_run():
    """Enable/disable dry run mode"""
    try:
        data = request.get_json(force=True)
        enabled = data.get("enabled", True)
        set_dry_run_mode(enabled)

        audit("set_dry_run", {"enabled": enabled})
        return jsonify({
            "dry_run_enabled": enabled,
            "message": f"Dry run mode {'enabled' if enabled else 'disabled'}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/config/status", methods=['GET'])
def config_status():
    """Get current configuration status"""
    try:
        return jsonify(get_integration_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Meeting Notes ---
@app.route("/api/meetings/<meeting_id>/notes", methods=['GET'])
def get_meeting_notes(meeting_id: str):
    """Retrieve stored notes for a meeting."""
    try:
        notes = memory_service.get_meeting_notes(meeting_id)
        return jsonify({"meeting_id": meeting_id, "notes": notes})
    except Exception as e:
        log.error(f"Error retrieving notes for meeting {meeting_id}: {e}")
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
