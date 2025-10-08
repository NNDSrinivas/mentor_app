from __future__ import annotations

from flask import Blueprint, jsonify, request

from .jira_service import JiraIntegrationService


bp = Blueprint("jira_integration", __name__)
service = JiraIntegrationService()


def _context():
    org_id, user_id = service.resolve_context(request.headers)
    return org_id, user_id


@bp.route("/api/integrations/jira/oauth/start", methods=["POST"])
def jira_oauth_start():
    state = request.json.get("state") if request.is_json else None
    payload = service.build_oauth_url(state=state)
    return jsonify(payload)


@bp.route("/api/integrations/jira/oauth/callback", methods=["GET"])
def jira_oauth_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing code"}), 400
    org_id, user_id = _context()
    tokens = service.exchange_code_for_tokens(code)
    cloud_base_url = request.args.get("cloud_base_url") or request.headers.get(
        "X-Jira-Base-Url", "https://example.atlassian.net"
    )
    connection = service.store_tokens(
        org_id=org_id,
        user_id=user_id,
        cloud_base_url=cloud_base_url,
        tokens=tokens,
    )
    return jsonify({"ok": True, "connection_id": str(connection.id)})


@bp.route("/api/integrations/jira/config", methods=["POST"])
def jira_config():
    if not request.is_json:
        return jsonify({"error": "invalid payload"}), 400
    data = request.get_json() or {}
    project_keys = data.get("project_keys") or []
    if not project_keys:
        return jsonify({"error": "project_keys required"}), 400
    org_id, user_id = _context()
    status = service.get_status(org_id)
    if not status.get("connected"):
        return jsonify({"error": "oauth required"}), 400

    connection_id = data.get("connection_id")
    if not connection_id:
        status = service.get_status(org_id)
        if not status.get("connected"):
            return jsonify({"error": "oauth required"}), 400
        # Fetch latest connection
        from backend.db.base import session_scope
        from backend.db.models import JiraConnection

        with session_scope() as session:
            connection = (
                session.query(JiraConnection)
                .filter(JiraConnection.org_id == org_id)
                .order_by(JiraConnection.created_at.desc())
                .first()
            )
            if not connection:
                return jsonify({"error": "oauth required"}), 400
            connection_id = connection.id

    config = service.update_project_config(
        org_id=org_id,
        connection_id=connection_id,
        project_keys=project_keys,
        board_ids=data.get("board_ids") or [],
        default_jql=data.get("default_jql"),
    )
    return jsonify({"ok": True, "config_id": str(config.id)})


@bp.route("/api/integrations/jira/status", methods=["GET"])
def jira_status():
    org_id, _ = _context()
    status = service.get_status(org_id)
    return jsonify(status)


@bp.route("/api/integrations/jira/sync", methods=["POST"])
def jira_sync():
    org_id, _ = _context()
    result = service.worker.enqueue(org_id)
    return jsonify(result)


@bp.route("/api/jira/tasks", methods=["GET"])
def jira_tasks():
    org_id, _ = _context()
    assignee = request.args.get("assignee")
    status = request.args.get("status")
    project = request.args.get("project")
    updated_since = request.args.get("updated_since")
    me_identifier = request.headers.get("X-Jira-User")
    tasks = service.list_tasks(
        org_id,
        assignee,
        status,
        project,
        updated_since,
        me_identifier=me_identifier,
    )
    return jsonify(tasks)


@bp.route("/api/jira/search", methods=["GET"])
def jira_search():
    org_id, _ = _context()
    query = request.args.get("q", "")
    project = request.args.get("project")
    try:
        top_k = int(request.args.get("top_k", 10))
    except ValueError:
        top_k = 10
    results = service.search(org_id, query, project, top_k=top_k)
    return jsonify(results)


@bp.route("/api/jira/issues/<key>", methods=["GET"])
def jira_issue(key: str):
    org_id, _ = _context()
    issue = service.get_issue(org_id, key)
    if not issue:
        return jsonify({"error": "not found"}), 404
    return jsonify(issue)


__all__ = ["bp", "service"]
