from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request

from backend.jira_integration import integration_service


bp = Blueprint("jira_integration", __name__)


def _parse_uuid(value: Optional[str], env_var: str) -> uuid.UUID:
    if value:
        try:
            return uuid.UUID(value)
        except ValueError:
            raise ValueError(f"Invalid UUID: {value}")
    env_default = os.getenv(env_var)
    if env_default:
        return uuid.UUID(env_default)
    # Deterministic fallback
    return uuid.uuid5(uuid.NAMESPACE_DNS, env_var)


def _resolve_org_id() -> uuid.UUID:
    header = request.headers.get("X-Org-Id") or request.args.get("org_id")
    return _parse_uuid(header, "DEFAULT_ORG_ID")


def _resolve_user_id() -> uuid.UUID:
    header = request.headers.get("X-User-Id") or request.args.get("user_id")
    return _parse_uuid(header, "DEFAULT_USER_ID")


def _resolve_assignee(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value.lower() != "me":
        return value
    return request.headers.get("X-User-Name") or request.headers.get("X-User-Email")


@bp.route("/api/integrations/jira/oauth/start", methods=["POST"])
def jira_oauth_start():
    org_id = _resolve_org_id()
    user_id = _resolve_user_id()
    payload = request.get_json(silent=True) or {}
    scopes = payload.get("scopes")
    if scopes and not isinstance(scopes, list):
        return jsonify({"error": "scopes must be an array"}), 400
    result = integration_service.start_oauth(org_id, user_id, scopes=scopes)
    return jsonify(result)


@bp.route("/api/integrations/jira/oauth/callback", methods=["GET"])
def jira_oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    try:
        result = integration_service.complete_oauth(code, state=state)
    except Exception as exc:  # pragma: no cover - error path
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/api/integrations/jira/config", methods=["POST"])
def jira_config_update():
    org_id = _resolve_org_id()
    user_id = _resolve_user_id()
    payload = request.get_json(force=True)
    project_keys = payload.get("project_keys") or []
    if not isinstance(project_keys, list) or not project_keys:
        return jsonify({"error": "project_keys must be a non-empty array"}), 400
    board_ids = payload.get("board_ids") or []
    default_jql = payload.get("default_jql")
    result = integration_service.update_project_config(
        org_id,
        user_id,
        project_keys=project_keys,
        board_ids=board_ids,
        default_jql=default_jql,
    )
    return jsonify(result)


@bp.route("/api/integrations/jira/status", methods=["GET"])
def jira_status():
    org_id = _resolve_org_id()
    result = integration_service.get_status(org_id)
    return jsonify(result)


@bp.route("/api/integrations/jira/sync", methods=["POST"])
def jira_sync():
    org_id = _resolve_org_id()
    payload = request.get_json(silent=True) or {}
    if payload.get("run_now"):
        result = integration_service.sync_now(org_id)
        return jsonify({"fetched": result.fetched, "updated": result.updated, "indexed": result.indexed})
    result = integration_service.trigger_sync(org_id)
    return jsonify(result)


@bp.route("/api/jira/tasks", methods=["GET"])
def jira_tasks():
    org_id = _resolve_org_id()
    assignee = _resolve_assignee(request.args.get("assignee"))
    status = request.args.get("status")
    project = request.args.get("project")
    updated_since_raw = request.args.get("updated_since")
    updated_since = None
    if updated_since_raw:
        try:
            updated_since = datetime.fromisoformat(updated_since_raw)
        except ValueError:
            return jsonify({"error": "Invalid updated_since timestamp"}), 400
    tasks = integration_service.list_tasks(
        org_id,
        assignee=assignee,
        status=status,
        project=project,
        updated_since=updated_since,
    )
    return jsonify(tasks)


@bp.route("/api/jira/search", methods=["GET"])
def jira_search():
    org_id = _resolve_org_id()
    query = request.args.get("q", "")
    project = request.args.get("project")
    try:
        top_k = int(request.args.get("top_k", "10"))
    except ValueError:
        return jsonify({"error": "Invalid top_k"}), 400
    results = integration_service.search(org_id, query, project=project, top_k=top_k)
    return jsonify(results)


@bp.route("/api/jira/issues/<issue_key>", methods=["GET"])
def jira_issue_detail(issue_key: str):
    org_id = _resolve_org_id()
    result = integration_service.get_issue(org_id, issue_key)
    if not result:
        return jsonify({"error": "Not Found"}), 404
    return jsonify(result)


__all__ = ["bp"]
