from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.base import session_scope
from backend.db.models import JiraConnection, JiraIssue, JiraProjectConfig

from .jira_crypto import JiraTokenCipher
from .jira_vector_store import JiraIssueVectorStore


DEFAULT_RETRY_BACKOFF = [1, 2, 4, 8]
FIXTURES_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "jira")
)


def _parse_uuid(value: str, fallback_namespace: uuid.UUID) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except Exception:
        return uuid.uuid5(fallback_namespace, str(value))


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_updated_since(value: Optional[str]) -> Optional[dt.datetime]:
    """Parse query parameters that may omit time information."""

    if not value:
        return None

    parsed = _parse_datetime(value)
    if parsed:
        return parsed

    candidates = [value, f"{value}T00:00:00", f"{value}T00:00:00+00:00"]
    for candidate in candidates:
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def _stringify_scopes(scopes: str | List[str] | None) -> List[str]:
    if scopes is None:
        return []
    if isinstance(scopes, str):
        return [scope.strip() for scope in scopes.split(" ") if scope.strip()]
    return scopes


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: List[str]


class JiraSyncWorker:
    """Simple background worker for Jira sync operations."""

    def __init__(self, service: "JiraIntegrationService") -> None:
        self._service = service
        self._lock = threading.Lock()
        self._pending: set[uuid.UUID] = set()
        self._threads: List[threading.Thread] = []

    def enqueue(self, org_id: uuid.UUID) -> Dict[str, Any]:
        inline = os.getenv("JIRA_SYNC_INLINE", "false").lower() == "true"
        if inline:
            summary = self._service.perform_sync(org_id)
            summary["mode"] = "inline"
            return summary

        with self._lock:
            if org_id in self._pending:
                return {"queued": False, "message": "sync already running"}
            self._pending.add(org_id)

        thread = threading.Thread(target=self._run, args=(org_id,), daemon=True)
        self._threads.append(thread)
        thread.start()
        return {"queued": True}

    def _run(self, org_id: uuid.UUID) -> None:
        try:
            self._service.perform_sync(org_id)
        finally:
            with self._lock:
                self._pending.discard(org_id)


class JiraIntegrationService:
    """Service encapsulating Jira OAuth, configuration, sync and search."""

    def __init__(self, *, vector_store: Optional[JiraIssueVectorStore] = None) -> None:
        self.mock_mode = os.getenv("MOCK_JIRA", "false").lower() == "true"
        self.cipher = JiraTokenCipher()
        self.vector_store = vector_store or JiraIssueVectorStore()
        self.worker = JiraSyncWorker(self)

    # ------------------------------------------------------------------
    # Query filtering helpers
    def _prepare_issue_filters(
        self,
        connection: Optional[JiraConnection],
        assignee: Optional[str],
        status: Optional[str],
        updated_since: Optional[str],
        me_identifier: Optional[str],
    ) -> Tuple[List[str], Optional[dt.datetime], Optional[str]]:
        statuses: List[str] = []
        if status:
            statuses = [item.strip() for item in status.split(",") if item.strip()]

        since_dt = _parse_updated_since(updated_since)

        assignee_value: Optional[str] = None
        if assignee:
            if assignee.lower() == "me":
                assignee_value = me_identifier or (
                    str(connection.user_id) if connection is not None else None
                )
            else:
                assignee_value = assignee

        return statuses, since_dt, assignee_value

    def _apply_issue_filters(
        self,
        query,
        project: Optional[str],
        statuses: List[str],
        since_dt: Optional[dt.datetime],
        assignee_value: Optional[str],
    ):
        if project:
            query = query.filter(JiraIssue.project_key == project)
        if statuses:
            query = query.filter(JiraIssue.status.in_(statuses))
        if since_dt:
            query = query.filter(JiraIssue.updated >= since_dt)
        if assignee_value:
            query = query.filter(JiraIssue.assignee == assignee_value)
        return query

    # ------------------------------------------------------------------
    # Context helpers
    def resolve_context(self, headers: Dict[str, str]) -> Tuple[uuid.UUID, uuid.UUID]:
        namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
        org_raw = headers.get("X-Org-ID") or os.getenv("DEFAULT_ORG_ID", "org-default")
        user_raw = headers.get("X-User-ID") or headers.get("X-User-Email") or os.getenv(
            "DEFAULT_USER_ID", "user-default"
        )
        org_id = _parse_uuid(org_raw, namespace)
        user_id = _parse_uuid(user_raw, org_id)
        return org_id, user_id

    # ------------------------------------------------------------------
    # OAuth
    def build_oauth_url(self, state: Optional[str] = None) -> Dict[str, str]:
        if self.mock_mode:
            return {"url": "https://mock.atlassian.net/oauth"}

        client_id = os.getenv("JIRA_CLIENT_ID", "")
        redirect_uri = os.getenv("JIRA_REDIRECT_URI", "http://localhost:5000/api/integrations/jira/oauth/callback")
        scope = os.getenv(
            "JIRA_DEFAULT_SCOPES",
            "read:jira-user read:jira-work offline_access",
        )
        authorize_base = "https://auth.atlassian.com/authorize"
        params = {
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        query = "&".join(f"{key}={requests.utils.quote(str(value))}" for key, value in params.items())
        return {"url": f"{authorize_base}?{query}"}

    def exchange_code_for_tokens(self, code: str) -> OAuthTokens:
        if self.mock_mode:
            fixture_path = os.path.join(FIXTURES_ROOT, "oauth_tokens.json")
            with open(fixture_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            client_id = os.getenv("JIRA_CLIENT_ID", "")
            client_secret = os.getenv("JIRA_CLIENT_SECRET", "")
            redirect_uri = os.getenv(
                "JIRA_REDIRECT_URI", "http://localhost:5000/api/integrations/jira/oauth/callback"
            )
            token_endpoint = "https://auth.atlassian.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }
            response = requests.post(token_endpoint, json=data, timeout=30)
            response.raise_for_status()
            payload = response.json()

        scopes = _stringify_scopes(payload.get("scope"))
        return OAuthTokens(
            access_token=payload.get("access_token", ""),
            refresh_token=payload.get("refresh_token", ""),
            token_type=payload.get("token_type", "Bearer"),
            expires_in=int(payload.get("expires_in", 3600)),
            scope=scopes,
        )

    def store_tokens(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        cloud_base_url: str,
        tokens: OAuthTokens,
    ) -> JiraConnection:
        with session_scope() as session:
            connection = (
                session.execute(
                    select(JiraConnection).where(
                        JiraConnection.org_id == org_id,
                        JiraConnection.user_id == user_id,
                    )
                )
                .scalars()
                .one_or_none()
            )

            expires_at = _now() + dt.timedelta(seconds=tokens.expires_in - 30)
            encrypted_access = self.cipher.encrypt(tokens.access_token)
            encrypted_refresh = self.cipher.encrypt(tokens.refresh_token)

            if connection is None:
                connection = JiraConnection(
                    org_id=org_id,
                    user_id=user_id,
                    cloud_base_url=cloud_base_url,
                    client_id=os.getenv("JIRA_CLIENT_ID", ""),
                    token_type=tokens.token_type,
                    access_token=encrypted_access,
                    refresh_token=encrypted_refresh,
                    expires_at=expires_at,
                    scopes=tokens.scope,
                )
                session.add(connection)
            else:
                connection.access_token = encrypted_access
                connection.refresh_token = encrypted_refresh
                connection.token_type = tokens.token_type
                connection.expires_at = expires_at
                connection.scopes = tokens.scope
                connection.cloud_base_url = cloud_base_url or connection.cloud_base_url
            session.flush()
            session.refresh(connection)
            return connection

    # ------------------------------------------------------------------
    # Status & Configuration
    def update_project_config(
        self,
        *,
        org_id: uuid.UUID,
        connection_id: uuid.UUID,
        project_keys: List[str],
        board_ids: Optional[List[str]],
        default_jql: Optional[str],
    ) -> JiraProjectConfig:
        with session_scope() as session:
            config = (
                session.execute(
                    select(JiraProjectConfig).where(
                        JiraProjectConfig.org_id == org_id,
                        JiraProjectConfig.connection_id == connection_id,
                    )
                )
                .scalars()
                .one_or_none()
            )

            if config is None:
                config = JiraProjectConfig(
                    org_id=org_id,
                    connection_id=connection_id,
                    project_keys=project_keys,
                    board_ids=board_ids or [],
                    default_jql=default_jql,
                )
                session.add(config)
            else:
                config.project_keys = project_keys
                config.board_ids = board_ids or []
                config.default_jql = default_jql
            session.flush()
            session.refresh(config)
            return config

    def get_status(self, org_id: uuid.UUID) -> Dict[str, Any]:
        with session_scope() as session:
            connection = (
                session.execute(
                    select(JiraConnection).where(JiraConnection.org_id == org_id).order_by(JiraConnection.created_at.desc())
                )
                .scalars()
                .first()
            )

            if not connection:
                return {"connected": False, "projects": [], "last_sync_at": None, "scopes": []}

            config = (
                session.execute(
                    select(JiraProjectConfig).where(JiraProjectConfig.connection_id == connection.id)
                )
                .scalars()
                .first()
            )

            return {
                "connected": True,
                "last_sync_at": config.last_sync_at.isoformat() if config and config.last_sync_at else None,
                "projects": config.project_keys if config else [],
                "scopes": connection.scopes or [],
            }

    # ------------------------------------------------------------------
    # Sync
    def perform_sync(self, org_id: uuid.UUID) -> Dict[str, Any]:
        processed = 0
        reindexed = 0
        with session_scope() as session:
            configs = (
                session.execute(select(JiraProjectConfig).where(JiraProjectConfig.org_id == org_id))
                .scalars()
                .all()
            )
            if not configs:
                return {"processed": 0, "reindexed": 0}

            for config in configs:
                connection = session.get(JiraConnection, config.connection_id)
                if connection is None:
                    continue
                connection = self.ensure_access_token(session, connection)
                issues = list(self._fetch_updated_issues(connection, config))
                for issue_payload in issues:
                    issue, reindexed_flag = self._upsert_issue(session, connection, issue_payload)
                    processed += 1
                    if reindexed_flag:
                        reindexed += 1
                config.last_sync_at = _now()
            session.flush()
        return {"processed": processed, "reindexed": reindexed}

    def ensure_access_token(self, session: Session, connection: JiraConnection) -> JiraConnection:
        expires_at = connection.expires_at or (_now() - dt.timedelta(seconds=1))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
        if expires_at - _now() > dt.timedelta(minutes=2):
            return connection

        if self.mock_mode:
            tokens = self.exchange_code_for_tokens("mock-refresh")
        else:
            token_endpoint = "https://auth.atlassian.com/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": connection.client_id,
                "client_secret": os.getenv("JIRA_CLIENT_SECRET", ""),
                "refresh_token": self.cipher.decrypt(connection.refresh_token) or "",
            }
            response = requests.post(token_endpoint, json=data, timeout=30)
            response.raise_for_status()
            payload = response.json()
            tokens = OAuthTokens(
                access_token=payload.get("access_token", ""),
                refresh_token=payload.get("refresh_token", data["refresh_token"]),
                token_type=payload.get("token_type", connection.token_type or "Bearer"),
                expires_in=int(payload.get("expires_in", 3600)),
                scope=_stringify_scopes(payload.get("scope", connection.scopes or [])),
            )

        connection.access_token = self.cipher.encrypt(tokens.access_token)
        connection.refresh_token = self.cipher.encrypt(tokens.refresh_token)
        connection.token_type = tokens.token_type
        connection.scopes = tokens.scope
        connection.expires_at = _now() + dt.timedelta(seconds=tokens.expires_in - 30)
        session.add(connection)
        session.flush()
        session.refresh(connection)
        return connection

    def _fetch_updated_issues(
        self, connection: JiraConnection, config: JiraProjectConfig
    ) -> Iterable[Dict[str, Any]]:
        if self.mock_mode:
            if not os.path.isdir(FIXTURES_ROOT):
                return
            pages = sorted(
                [p for p in os.listdir(FIXTURES_ROOT) if p.startswith("search_page")],
                key=lambda name: name,
            )
            for page in pages:
                with open(os.path.join(FIXTURES_ROOT, page), "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                for issue in payload.get("issues", []):
                    yield issue
            return

        jql = config.default_jql or ""
        if not jql:
            keys = ",".join(config.project_keys)
            jql = f"project in ({keys})"
        if config.last_sync_at:
            since = config.last_sync_at - dt.timedelta(minutes=5)
            since_str = since.strftime("%Y-%m-%d %H:%M")
            jql += f" AND updated >= '{since_str}'"

        start_at = 0
        more = True
        while more:
            response = self._request_with_retry(
                "GET",
                f"https://api.atlassian.com/ex/jira/{self._cloud_id_from_base(connection.cloud_base_url)}/rest/api/3/search",
                headers=self._auth_headers(connection),
                params={"jql": jql, "startAt": start_at, "maxResults": 100},
            )
            response.raise_for_status()
            payload = response.json()
            issues = payload.get("issues", [])
            for issue in issues:
                yield issue
            total = payload.get("total", 0)
            start_at += len(issues)
            more = start_at < total and len(issues) > 0

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        backoff_sequence = list(DEFAULT_RETRY_BACKOFF)
        for attempt in range(len(backoff_sequence)):
            response = requests.request(method, url, timeout=30, **kwargs)
            if response.status_code != 429:
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else backoff_sequence[attempt]
            time.sleep(min(delay, 5))
        # Final attempt after all backoff intervals
        response = requests.request(method, url, timeout=30, **kwargs)
        return response

    def _cloud_id_from_base(self, base_url: str) -> str:
        cleaned = base_url.rstrip("/")
        return cleaned.split("//")[-1].split(".")[0]

    def _auth_headers(self, connection: JiraConnection) -> Dict[str, str]:
        token = self.cipher.decrypt(connection.access_token) or ""
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _upsert_issue(
        self,
        session: Session,
        connection: JiraConnection,
        issue_payload: Dict[str, Any],
    ) -> Tuple[JiraIssue, bool]:
        key = issue_payload.get("key")
        fields = issue_payload.get("fields", {})
        project_key = issue_payload.get("key", "").split("-")[0]
        summary = fields.get("summary")
        description = fields.get("description")
        if isinstance(description, dict):
            description = description.get("content") or json.dumps(description)
        status_name = (fields.get("status") or {}).get("name")
        priority_name = (fields.get("priority") or {}).get("name")
        assignee = (fields.get("assignee") or {}).get("displayName")
        reporter = (fields.get("reporter") or {}).get("displayName")
        labels = fields.get("labels") or []
        epic_key = None
        if fields.get("epic"):
            epic_key = fields["epic"].get("key")
        sprint = None
        if fields.get("sprint"):
            sprint = fields["sprint"].get("name")
        updated = _parse_datetime(fields.get("updated")) or _now()
        url = f"{connection.cloud_base_url.rstrip('/')}/browse/{key}"

        issue = (
            session.execute(select(JiraIssue).where(JiraIssue.issue_key == key))
            .scalars()
            .one_or_none()
        )

        reindexed = False
        if issue is None:
            issue = JiraIssue(
                connection_id=connection.id,
                project_key=project_key,
                issue_key=key,
                summary=summary,
                description=description,
                status=status_name,
                priority=priority_name,
                assignee=assignee,
                reporter=reporter,
                labels=labels,
                epic_key=epic_key,
                sprint=sprint,
                updated=updated,
                url=url,
                raw=issue_payload,
            )
            session.add(issue)
            reindexed = True
        else:
            changed_fields = [
                issue.summary != summary,
                issue.description != description,
                issue.status != status_name,
                issue.priority != priority_name,
                issue.assignee != assignee,
                issue.updated != updated,
            ]
            reindexed = any(changed_fields)
            issue.project_key = project_key
            issue.summary = summary
            issue.description = description
            issue.status = status_name
            issue.priority = priority_name
            issue.assignee = assignee
            issue.reporter = reporter
            issue.labels = labels
            issue.epic_key = epic_key
            issue.sprint = sprint
            issue.updated = updated
            issue.url = url
            issue.raw = issue_payload

        if reindexed:
            combined_text = "\n".join(
                filter(
                    None,
                    [summary or "", description or "", " ".join(labels or [])],
                )
            )
            self.vector_store.index_issue(
                issue.issue_key,
                combined_text,
                {
                    "issue_key": issue.issue_key,
                    "summary": summary or "",
                    "project": project_key,
                    "status": status_name or "",
                },
            )
            issue.indexed_at = _now()

        session.flush()
        session.refresh(issue)
        return issue, reindexed

    # ------------------------------------------------------------------
    # Queries
    def list_tasks(
        self,
        org_id: uuid.UUID,
        assignee: Optional[str],
        status: Optional[str],
        project: Optional[str],
        updated_since: Optional[str],
        me_identifier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with session_scope() as session:
            connection = (
                session.execute(select(JiraConnection).where(JiraConnection.org_id == org_id))
                .scalars()
                .first()
            )
            if not connection:
                return []

            statuses, since_dt, assignee_value = self._prepare_issue_filters(
                connection,
                assignee,
                status,
                updated_since,
                me_identifier,
            )

            query = session.query(JiraIssue).join(
                JiraProjectConfig, JiraProjectConfig.connection_id == JiraIssue.connection_id
            )
            query = query.filter(JiraProjectConfig.org_id == org_id)
            query = self._apply_issue_filters(query, project, statuses, since_dt, assignee_value)

            results = []
            for issue in query.order_by(JiraIssue.updated.desc()).all():
                results.append(
                    {
                        "key": issue.issue_key,
                        "title": issue.summary,
                        "status": issue.status,
                        "priority": issue.priority,
                        "assignee": issue.assignee,
                        "updated": issue.updated.isoformat() if issue.updated else None,
                        "url": issue.url,
                    }
                )
            return results

    def search(
        self,
        org_id: uuid.UUID,
        query: str,
        project: Optional[str],
        *,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        updated_since: Optional[str] = None,
        top_k: int = 10,
        me_identifier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []
        with session_scope() as session:
            connection = (
                session.execute(select(JiraConnection).where(JiraConnection.org_id == org_id))
                .scalars()
                .first()
            )
            if not connection:
                return []

            statuses, since_dt, assignee_value = self._prepare_issue_filters(
                connection,
                assignee,
                status,
                updated_since,
                me_identifier,
            )

            base_query = session.query(JiraIssue).join(
                JiraProjectConfig, JiraProjectConfig.connection_id == JiraIssue.connection_id
            )
            base_query = base_query.filter(JiraProjectConfig.org_id == org_id)
            base_query = self._apply_issue_filters(
                base_query, project, statuses, since_dt, assignee_value
            )
            text_matches = (
                base_query.filter(
                    func.lower(JiraIssue.summary).contains(query.lower())
                    | func.lower(JiraIssue.description).contains(query.lower())
                )
                .limit(top_k)
                .all()
            )
            vector_scores = self.vector_store.search(query, limit=top_k)
            scored: Dict[str, Tuple[float, JiraIssue]] = {}
            for issue in text_matches:
                scored[issue.issue_key] = (0.0, issue)
            # Bulk fetch all issues for vector search results in one query
            vector_issue_keys = list(vector_scores.keys())
            if vector_issue_keys:
                vector_query = session.query(JiraIssue).join(
                    JiraProjectConfig,
                    JiraProjectConfig.connection_id == JiraIssue.connection_id,
                )
                vector_query = vector_query.filter(
                    JiraProjectConfig.org_id == org_id,
                    JiraIssue.issue_key.in_(vector_issue_keys),
                )
                vector_query = self._apply_issue_filters(
                    vector_query, project, statuses, since_dt, assignee_value
                )
                vector_issues = vector_query.all()
                # Map issue_key to JiraIssue object
                issue_map = {issue.issue_key: issue for issue in vector_issues}
                for issue_key, distance in vector_scores.items():
                    issue = issue_map.get(issue_key)
                    if issue is None:
                        continue
                    score = distance
                    if issue.issue_key in scored:
                        score = min(score, scored[issue.issue_key][0])
                    scored[issue.issue_key] = (score, issue)

            ranked = sorted(scored.values(), key=lambda item: item[0])[:top_k]
            return [self._issue_to_dict(issue) for _, issue in ranked]

    def get_issue(self, org_id: uuid.UUID, key: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            issue = (
                session.execute(
                    select(JiraIssue)
                    .join(JiraProjectConfig, JiraProjectConfig.connection_id == JiraIssue.connection_id)
                    .where(
                        JiraIssue.issue_key == key,
                        JiraProjectConfig.org_id == org_id,
                    )
                )
                .scalars()
                .one_or_none()
            )
            if not issue:
                return None
            return self._issue_to_dict(issue, include_raw=True)

    def _issue_to_dict(self, issue: JiraIssue, include_raw: bool = False) -> Dict[str, Any]:
        payload = {
            "key": issue.issue_key,
            "project": issue.project_key,
            "title": issue.summary,
            "summary": issue.summary,
            "description": issue.description,
            "status": issue.status,
            "priority": issue.priority,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "labels": issue.labels or [],
            "epic_key": issue.epic_key,
            "sprint": issue.sprint,
            "updated": issue.updated.isoformat() if issue.updated else None,
            "url": issue.url,
        }
        if include_raw:
            payload["raw"] = issue.raw
        return payload


__all__ = ["JiraIntegrationService", "JiraSyncWorker", "OAuthTokens"]
