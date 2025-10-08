from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.base import session_scope
from backend.db.models import JiraConnection, JiraIssue, JiraProjectConfig
from backend.jira_vector_store import JiraVectorStore


JIRA_OAUTH_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
JIRA_OAUTH_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _default_org_id() -> uuid.UUID:
    raw = os.getenv("DEFAULT_ORG_ID", "00000000-0000-4000-8000-000000000000")
    return uuid.UUID(raw)


def _default_user_id() -> uuid.UUID:
    raw = os.getenv("DEFAULT_USER_ID", "00000000-0000-4000-8000-000000000001")
    return uuid.UUID(raw)


def _fernet_key() -> bytes:
    raw = os.getenv("JIRA_ENCRYPTION_KEY")
    if raw:
        try:
            # Allow passing pre-encoded key
            Fernet(raw.encode())
            return raw.encode()
        except Exception:
            pass
        digest = hashlib.sha256(raw.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
    digest = hashlib.sha256(b"mentor-app-jira-secret").digest()
    return base64.urlsafe_b64encode(digest)


_FERNET = Fernet(_fernet_key())


def _encrypt(value: str | None) -> str:
    if value is None:
        return ""
    return _FERNET.encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str | None) -> str:
    if not value:
        return ""
    return _FERNET.decrypt(value.encode("utf-8")).decode("utf-8")


def _parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def _load_mock_fixture(name: str) -> Dict[str, object]:
    base = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "jira"
    path = base / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class JiraSyncResult:
    fetched: int
    updated: int
    indexed: int


class JiraIntegrationService:
    def __init__(self) -> None:
        self._vector_store = JiraVectorStore()
        self._state_cache: Dict[str, Tuple[uuid.UUID, uuid.UUID]] = {}
        self._sync_lock = threading.Lock()

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------
    def start_oauth(self, org_id: uuid.UUID, user_id: uuid.UUID, scopes: Optional[List[str]] = None) -> Dict[str, str]:
        state = uuid.uuid4().hex
        self._state_cache[state] = (org_id, user_id)

        if os.getenv("MOCK_JIRA", "false").lower() == "true":
            return {"auth_url": "mock://jira/oauth", "state": state}

        client_id = os.getenv("JIRA_CLIENT_ID")
        redirect_uri = os.getenv("JIRA_REDIRECT_URI")
        if not client_id or not redirect_uri:
            raise RuntimeError("Missing JIRA_CLIENT_ID or JIRA_REDIRECT_URI environment variables")

        scope_param = " ".join(scopes or os.getenv("JIRA_SCOPES", "offline_access read:jira-work manage:jira-project").split())
        params = {
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": scope_param,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        query = "&".join(f"{key}={requests.utils.quote(str(value))}" for key, value in params.items())
        return {"auth_url": f"{JIRA_OAUTH_AUTHORIZE_URL}?{query}", "state": state}

    def complete_oauth(self, code: str, state: Optional[str] = None) -> Dict[str, object]:
        org_id, user_id = self._state_cache.pop(state or "", (_default_org_id(), _default_user_id()))
        mock_mode = os.getenv("MOCK_JIRA", "false").lower() == "true"

        with session_scope() as session:
            existing = self._get_connection(session, org_id)
            if mock_mode:
                connection = self._create_or_update_mock_connection(session, existing, org_id, user_id)
            else:
                connection = self._exchange_code_for_tokens(session, existing, org_id, user_id, code)

        return {
            "connected": True,
            "connection_id": str(connection.id),
            "org_id": str(connection.org_id),
            "scopes": connection.scopes or [],
        }

    def _create_or_update_mock_connection(
        self,
        session: Session,
        existing: Optional[JiraConnection],
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> JiraConnection:
        base_url = os.getenv("JIRA_CLOUD_BASE_URL", "https://mock-jira.example.com")
        access_token = _encrypt("mock-access-token")
        refresh_token = _encrypt("mock-refresh-token")
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.expires_at = _now() + timedelta(hours=1)
            existing.scopes = ["read:jira-work", "offline_access"]
            session.add(existing)
            session.flush()
            return existing

        connection = JiraConnection(
            org_id=org_id,
            user_id=user_id,
            cloud_base_url=base_url,
            client_id="mock-client",
            token_type="Bearer",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=_now() + timedelta(hours=1),
            scopes=["read:jira-work", "offline_access"],
        )
        session.add(connection)
        session.flush()
        return connection

    def _exchange_code_for_tokens(
        self,
        session: Session,
        existing: Optional[JiraConnection],
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        code: str,
    ) -> JiraConnection:
        client_id = os.getenv("JIRA_CLIENT_ID")
        client_secret = os.getenv("JIRA_CLIENT_SECRET")
        redirect_uri = os.getenv("JIRA_REDIRECT_URI")
        if not client_id or not client_secret or not redirect_uri:
            raise RuntimeError("Missing JIRA OAuth configuration")

        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        response = requests.post(JIRA_OAUTH_TOKEN_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        token_type = data.get("token_type", "Bearer")
        scope_raw = data.get("scope", "")
        scopes = [scope for scope in scope_raw.split() if scope]

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resources_resp = requests.get(ACCESSIBLE_RESOURCES_URL, headers=headers, timeout=30)
        resources_resp.raise_for_status()
        resources = resources_resp.json() or []
        cloud_base_url = resources[0].get("url") if resources else os.getenv("JIRA_CLOUD_BASE_URL")
        if not cloud_base_url:
            raise RuntimeError("Unable to resolve Jira cloud base URL")

        expires_at = _now() + timedelta(seconds=int(expires_in))
        encrypted_access = _encrypt(access_token)
        encrypted_refresh = _encrypt(refresh_token)

        if existing:
            existing.access_token = encrypted_access
            existing.refresh_token = encrypted_refresh
            existing.expires_at = expires_at
            existing.token_type = token_type
            existing.scopes = scopes
            existing.cloud_base_url = cloud_base_url
            session.add(existing)
            session.flush()
            return existing

        connection = JiraConnection(
            org_id=org_id,
            user_id=user_id,
            cloud_base_url=cloud_base_url,
            client_id=client_id,
            token_type=token_type,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_at=expires_at,
            scopes=scopes,
        )
        session.add(connection)
        session.flush()
        return connection

    # ------------------------------------------------------------------
    # Configuration & Status
    # ------------------------------------------------------------------
    def update_project_config(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        project_keys: List[str],
        board_ids: Optional[List[str]] = None,
        default_jql: Optional[str] = None,
    ) -> Dict[str, object]:
        with session_scope() as session:
            connection = self._get_connection(session, org_id)
            if not connection:
                raise RuntimeError("Jira connection not found for organization")

            config = (
                session.execute(
                    select(JiraProjectConfig).where(
                        JiraProjectConfig.org_id == org_id,
                        JiraProjectConfig.connection_id == connection.id,
                    )
                )
                .scalars()
                .first()
            )
            if config:
                config.project_keys = project_keys
                config.board_ids = board_ids or []
                config.default_jql = default_jql
                session.add(config)
                session.flush()
            else:
                config = JiraProjectConfig(
                    org_id=org_id,
                    connection_id=connection.id,
                    project_keys=project_keys,
                    board_ids=board_ids or [],
                    default_jql=default_jql,
                )
                session.add(config)
                session.flush()

            return {
                "config_id": str(config.id),
                "project_keys": config.project_keys,
                "board_ids": config.board_ids or [],
                "default_jql": config.default_jql,
            }

    def get_status(self, org_id: uuid.UUID) -> Dict[str, object]:
        with session_scope() as session:
            connection = self._get_connection(session, org_id)
            if not connection:
                return {"connected": False, "projects": [], "scopes": []}

            config = (
                session.execute(
                    select(JiraProjectConfig).where(
                        JiraProjectConfig.connection_id == connection.id,
                        JiraProjectConfig.org_id == org_id,
                    )
                )
                .scalars()
                .first()
            )
            projects = config.project_keys if config else []
            last_sync = _format_datetime(config.last_sync_at if config else None)

            return {
                "connected": True,
                "last_sync_at": last_sync,
                "projects": projects,
                "scopes": connection.scopes or [],
            }

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------
    def trigger_sync(self, org_id: uuid.UUID) -> Dict[str, object]:
        thread = threading.Thread(target=self._sync_worker, args=(org_id,), daemon=True)
        thread.start()
        return {"enqueued": True}

    def _sync_worker(self, org_id: uuid.UUID) -> None:
        with self._sync_lock:
            try:
                self.sync_now(org_id)
            except Exception:
                # swallow exceptions to avoid crashing the worker thread
                pass

    def sync_now(self, org_id: uuid.UUID) -> JiraSyncResult:
        mock_mode = os.getenv("MOCK_JIRA", "false").lower() == "true"
        fetched = 0
        updated = 0
        indexed = 0

        with session_scope() as session:
            connection = self._get_connection(session, org_id)
            if not connection:
                return JiraSyncResult(fetched=0, updated=0, indexed=0)

            config = (
                session.execute(
                    select(JiraProjectConfig).where(
                        JiraProjectConfig.connection_id == connection.id,
                        JiraProjectConfig.org_id == org_id,
                    )
                )
                .scalars()
                .first()
            )
            if not config or not config.project_keys:
                return JiraSyncResult(fetched=0, updated=0, indexed=0)

            since = (config.last_sync_at or (_now() - timedelta(days=30))) - timedelta(minutes=5)
            since_str = since.strftime("%Y-%m-%d %H:%M")
            base_jql = config.default_jql or f"project in ({','.join(config.project_keys)})"
            jql = f"({base_jql}) AND updated >= \"{since_str}\""

            access_token = self._ensure_access_token(session, connection)

            issue_payloads = list(self._fetch_issues(connection, access_token, jql, mock_mode=mock_mode))
            fetched = len(issue_payloads)
            now = _now()

            indexed_payload: List[Tuple[str, str, Dict[str, str]]] = []
            for payload in issue_payloads:
                issue, created = self._upsert_issue(session, connection, payload, now)
                if created:
                    updated += 1
                doc = self._compose_index_document(issue)
                metadata = {
                    "summary": issue.summary or "",
                    "status": issue.status or "",
                    "assignee": issue.assignee or "",
                    "project": issue.project_key or "",
                }
                indexed_payload.append((issue.issue_key, doc, metadata))
            config.last_sync_at = now
            session.add(config)
            session.flush()

        for issue_key, document, metadata in indexed_payload:
            self._vector_store.index_issue(issue_key, document, metadata)
            indexed += 1

        return JiraSyncResult(fetched=fetched, updated=updated, indexed=indexed)

    def _ensure_access_token(self, session: Session, connection: JiraConnection) -> str:
        expires_at = connection.expires_at or (_now() - timedelta(seconds=1))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > _now() + timedelta(seconds=30):
            return _decrypt(connection.access_token)

        if os.getenv("MOCK_JIRA", "false").lower() == "true":
            connection.access_token = _encrypt("mock-access-token")
            connection.expires_at = _now() + timedelta(hours=1)
            session.add(connection)
            session.flush()
            return "mock-access-token"

        client_id = connection.client_id
        client_secret = os.getenv("JIRA_CLIENT_SECRET")
        refresh_token = _decrypt(connection.refresh_token)
        if not client_id or not client_secret:
            raise RuntimeError("Missing client credentials for Jira refresh")

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
        response = requests.post(JIRA_OAUTH_TOKEN_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        connection.access_token = _encrypt(access_token)
        connection.expires_at = _now() + timedelta(seconds=int(expires_in))
        session.add(connection)
        session.flush()
        return access_token

    def _fetch_issues(
        self,
        connection: JiraConnection,
        access_token: str,
        jql: str,
        mock_mode: bool = False,
        max_results: int = 100,
    ) -> Iterable[Dict[str, object]]:
        if mock_mode:
            data = _load_mock_fixture("issues.json")
            issues = data.get("issues", []) if isinstance(data, dict) else []
            for item in issues:
                yield item
            return

        base_url = connection.cloud_base_url.rstrip("/")
        url = f"{base_url}/rest/api/3/search"
        start_at = 0
        total = None
        backoff = 1

        while total is None or start_at < total:
            params = {"jql": jql, "maxResults": max_results, "startAt": start_at}
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", backoff))
                time.sleep(min(retry_after, 30))
                backoff = min(backoff * 2, 60)
                continue
            response.raise_for_status()
            data = response.json()
            issues = data.get("issues", [])
            total = data.get("total", start_at + len(issues))
            for issue in issues:
                yield issue
            fetched_count = len(issues)
            if fetched_count == 0:
                break
            start_at += fetched_count

    def _upsert_issue(
        self,
        session: Session,
        connection: JiraConnection,
        payload: Dict[str, object],
        indexed_at: datetime,
    ) -> Tuple[JiraIssue, bool]:
        issue_key = str(payload.get("key"))
        fields = payload.get("fields", {}) if isinstance(payload.get("fields"), dict) else {}
        project = fields.get("project", {}) if isinstance(fields.get("project"), dict) else {}
        project_key = project.get("key") or issue_key.split("-")[0]
        summary = fields.get("summary")
        description_raw = fields.get("description")
        description = description_raw if isinstance(description_raw, str) else json.dumps(description_raw or {}) if description_raw else None
        status = (fields.get("status") or {}).get("name") if isinstance(fields.get("status"), dict) else None
        priority = (fields.get("priority") or {}).get("name") if isinstance(fields.get("priority"), dict) else None
        assignee = (fields.get("assignee") or {}).get("displayName") if isinstance(fields.get("assignee"), dict) else None
        reporter = (fields.get("reporter") or {}).get("displayName") if isinstance(fields.get("reporter"), dict) else None
        labels = fields.get("labels") if isinstance(fields.get("labels"), list) else []
        epic = (fields.get("epic") or {}).get("key") if isinstance(fields.get("epic"), dict) else None
        sprint = None
        if isinstance(fields.get("sprint"), dict):
            sprint = fields.get("sprint", {}).get("name")
        elif isinstance(fields.get("sprint"), list) and fields.get("sprint"):
            sprint = fields.get("sprint")[0].get("name")
        updated = _parse_datetime(fields.get("updated"))
        url = f"{connection.cloud_base_url.rstrip('/')}/browse/{issue_key}"

        issue = (
            session.execute(select(JiraIssue).where(JiraIssue.issue_key == issue_key))
            .scalars()
            .first()
        )
        created = False
        if issue:
            issue.summary = summary
            issue.description = description
            issue.status = status
            issue.priority = priority
            issue.assignee = assignee
            issue.reporter = reporter
            issue.labels = labels
            issue.epic_key = epic
            issue.sprint = sprint
            issue.updated = updated
            issue.url = url
            issue.raw = payload
            issue.indexed_at = indexed_at
        else:
            issue = JiraIssue(
                connection_id=connection.id,
                project_key=project_key,
                issue_key=issue_key,
                summary=summary,
                description=description,
                status=status,
                priority=priority,
                assignee=assignee,
                reporter=reporter,
                labels=labels,
                epic_key=epic,
                sprint=sprint,
                updated=updated,
                url=url,
                raw=payload,
                indexed_at=indexed_at,
            )
            session.add(issue)
            created = True
        session.flush()
        return issue, created

    def _compose_index_document(self, issue: JiraIssue) -> str:
        parts = [issue.summary or "", issue.description or "", " ".join(issue.labels or [])]
        return "\n".join(part for part in parts if part)

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------
    def list_tasks(
        self,
        org_id: uuid.UUID,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        project: Optional[str] = None,
        updated_since: Optional[datetime] = None,
    ) -> List[Dict[str, object]]:
        with session_scope() as session:
            query = (
                select(JiraIssue)
                .join(JiraConnection, JiraIssue.connection_id == JiraConnection.id)
                .where(JiraConnection.org_id == org_id)
            )

            if project:
                query = query.where(func.lower(JiraIssue.project_key) == project.lower())
            if assignee:
                query = query.where(func.lower(func.coalesce(JiraIssue.assignee, "")) == assignee.lower())
            if status:
                query = query.where(func.lower(func.coalesce(JiraIssue.status, "")) == status.lower())
            if updated_since:
                query = query.where(JiraIssue.updated != None, JiraIssue.updated >= updated_since)  # noqa: E711

            query = query.order_by(JiraIssue.updated.desc().nullslast())
            issues = session.execute(query).scalars().all()

        return [self._issue_to_dict(issue) for issue in issues]

    def search(
        self,
        org_id: uuid.UUID,
        query: str,
        project: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, object]]:
        project_filter = project.lower() if project else None

        with session_scope() as session:
            stmt = (
                select(JiraIssue)
                .join(JiraConnection, JiraIssue.connection_id == JiraConnection.id)
                .where(JiraConnection.org_id == org_id)
            )
            if project_filter:
                stmt = stmt.where(func.lower(JiraIssue.project_key) == project_filter)
            issues = session.execute(stmt).scalars().all()

        if not query.strip():
            return [self._issue_to_dict(issue) for issue in issues[:top_k]]

        vector_scores = {res.issue_key: res.score for res in self._vector_store.search(query, limit=top_k * 2)}
        ranked: List[Tuple[float, JiraIssue]] = []
        lowered_query = query.lower()
        for issue in issues:
            text = " ".join(filter(None, [issue.summary, issue.description, " ".join(issue.labels or [])])).lower()
            lexical = -2.0 if lowered_query and lowered_query in text else 0.0
            vector = vector_scores.get(issue.issue_key, 0.0)
            combined = lexical + vector
            ranked.append((combined, issue))

        ranked.sort(key=lambda item: item[0])
        return [self._issue_to_dict(issue) for _, issue in ranked[:top_k]]

    def get_issue(self, org_id: uuid.UUID, issue_key: str) -> Optional[Dict[str, object]]:
        with session_scope() as session:
            stmt = (
                select(JiraIssue)
                .join(JiraConnection, JiraIssue.connection_id == JiraConnection.id)
                .where(
                    JiraConnection.org_id == org_id,
                    func.lower(JiraIssue.issue_key) == issue_key.lower(),
                )
            )
            issue = session.execute(stmt).scalars().first()
        if not issue:
            return None
        return self._issue_to_dict(issue, include_raw=True)

    def _issue_to_dict(self, issue: JiraIssue, include_raw: bool = False) -> Dict[str, object]:
        data = {
            "key": issue.issue_key,
            "title": issue.summary,
            "status": issue.status,
            "priority": issue.priority,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "updated": _format_datetime(issue.updated),
            "url": issue.url,
            "project": issue.project_key,
            "labels": issue.labels or [],
            "epic_key": issue.epic_key,
            "sprint": issue.sprint,
        }
        if include_raw:
            data["description"] = issue.description
            data["raw"] = issue.raw
        return data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_connection(self, session: Session, org_id: uuid.UUID) -> Optional[JiraConnection]:
        return (
            session.execute(select(JiraConnection).where(JiraConnection.org_id == org_id))
            .scalars()
            .first()
        )


integration_service = JiraIntegrationService()


__all__ = ["integration_service", "JiraIntegrationService", "JiraSyncResult"]
