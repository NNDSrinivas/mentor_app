"""Service layer implementing the read-only GitHub integration features."""

from __future__ import annotations

import json
import os
import threading
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.db import session_scope
from backend.db.models import GHConnection, GHFile, GHIssuePR, GHRepo
from backend.github_integration.chunking import chunk_source, iter_language_from_path
from backend.security.crypto import TokenEncryptor


MAX_FILE_SIZE_BYTES = 256 * 1024
MAX_SNIPPET_LENGTH = 600
EXPECTED_INDEX_ERRORS = (
    FileNotFoundError,
    ValueError,
    RuntimeError,
    OSError,
    SQLAlchemyError,
)


def _now() -> datetime:
    return datetime.utcnow()


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat() + ("Z" if dt.tzinfo is None else "")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _tokenize(query: str) -> List[str]:
    return [part.lower() for part in query.split() if part.strip()]


def _score_text(tokens: Iterable[str], text: str, extra: str = "") -> float:
    if not tokens:
        return 0.0
    lower_text = text.lower()
    lower_extra = extra.lower()
    score = 0.0
    for token in tokens:
        occurrences = lower_text.count(token)
        score += occurrences * 1.5
        if token in lower_extra:
            score += 0.5
    return score


def _build_snippet(text: str, tokens: Iterable[str], limit: int = 320) -> str:
    snippet = text.strip()
    lower = snippet.lower()
    for token in tokens:
        idx = lower.find(token)
        if idx != -1:
            start = max(0, idx - 80)
            end = min(len(snippet), idx + 80)
            return snippet[start:end]
    return snippet[:limit]


@dataclass
class IndexJobStatus:
    id: str
    repo_full_name: str
    branch: str
    mode: str
    state: str = "queued"
    progress: float = 0.0
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "index_id": self.id,
            "state": self.state,
            "progress": round(self.progress, 3),
            "errors": self.errors,
            "started_at": _to_iso(self.started_at),
            "finished_at": _to_iso(self.finished_at),
        }


class GitHubIntegrationService:
    def __init__(self) -> None:
        self._encryptor = TokenEncryptor()
        self._jobs: Dict[str, IndexJobStatus] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    @property
    def mock_enabled(self) -> bool:
        return os.getenv("MOCK_GITHUB", "").lower() in {"1", "true", "yes", "on"}

    @property
    def fixtures_root(self) -> Path:
        root = os.getenv("GITHUB_FIXTURES_PATH")
        if root:
            return Path(root)
        return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mock_github"

    # ------------------------------------------------------------------
    def start_oauth(self) -> Dict[str, str]:
        client_id = os.getenv("GITHUB_CLIENT_ID", "mock-client-id")
        redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost/callback")
        scope = "read:user repo read:org"
        if self.mock_enabled:
            url = f"https://example.com/mock-github/oauth?client_id={client_id}"
        else:
            url = (
                "https://github.com/login/oauth/authorize"
                f"?client_id={client_id}&scope={scope.replace(' ', '%20')}"
                f"&redirect_uri={redirect_uri}"
            )
        return {"authorization_url": url}

    def complete_oauth(self, code: str) -> Dict[str, object]:
        access_token = self._exchange_token(code)
        with session_scope() as session:
            connection = session.execute(select(GHConnection)).scalars().first()
            if connection is None:
                connection = GHConnection(mock=self.mock_enabled)
                session.add(connection)
                session.flush()
            connection.encrypted_access_token = self._encryptor.encrypt(access_token)
            connection.updated_at = _now()
        return {"connected": True}

    def status(self) -> Dict[str, object]:
        with session_scope() as session:
            connection = session.execute(select(GHConnection)).scalars().first()
            connected = bool(connection and connection.encrypted_access_token)
            repos_indexed = session.execute(
                select(func.count()).select_from(GHRepo).where(GHRepo.last_index_at.isnot(None))
            ).scalar_one()
            last_index_at = session.execute(select(func.max(GHRepo.last_index_at))).scalar()
        return {
            "connected": connected,
            "repos_indexed": int(repos_indexed or 0),
            "last_index_at": _to_iso(last_index_at),
        }

    def list_repos(self) -> List[Dict[str, object]]:
        repos_payload = self._fetch_repos()
        results: List[Dict[str, object]] = []
        with session_scope() as session:
            connection = session.execute(select(GHConnection)).scalars().first()
            if connection is None:
                connection = GHConnection(mock=self.mock_enabled)
                session.add(connection)
                session.flush()
            for repo_payload in repos_payload:
                repo = self._upsert_repo(session, connection, repo_payload)
                results.append(
                    {
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "default_branch": repo.default_branch,
                        "private": bool(repo.private),
                        "url": repo.url,
                    }
                )
        return results

    def request_index(self, repo_full_name: str, branch: Optional[str] = None, mode: str = "api") -> Dict[str, str]:
        branch = branch or "main"
        index_id = str(uuid.uuid4())
        job = IndexJobStatus(id=index_id, repo_full_name=repo_full_name, branch=branch, mode=mode)
        with self._lock:
            self._jobs[index_id] = job
        thread = threading.Thread(
            target=self._run_index_job,
            args=(index_id, repo_full_name, branch, mode),
            daemon=True,
        )
        thread.start()
        return {"index_id": index_id}

    def index_status(self, index_id: str) -> Dict[str, object]:
        with self._lock:
            job = self._jobs.get(index_id)
        if job is None:
            return {"state": "unknown", "progress": 0.0, "errors": ["index job not found"]}
        return job.to_dict()

    def search_code(
        self, query: str, repo: Optional[str] = None, path: Optional[str] = None, top_k: int = 10
    ) -> List[Dict[str, object]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        stmt = select(GHFile, GHRepo).join(GHRepo, GHRepo.id == GHFile.repo_id)
        if repo:
            stmt = stmt.where(GHRepo.full_name == repo)
        if path:
            like = f"%{path}%"
            stmt = stmt.where(GHFile.path.like(like))
        with session_scope() as session:
            rows = session.execute(stmt).all()
        scored: List[Tuple[float, GHFile, GHRepo]] = []
        for file_row, repo_row in rows:
            score = _score_text(tokens, file_row.snippet, file_row.path)
            if score <= 0:
                continue
            scored.append((score, file_row, repo_row))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: List[Dict[str, object]] = []
        for score, file_row, repo_row in scored[:top_k]:
            sha = file_row.sha or repo_row.head_sha or repo_row.default_branch or "main"
            permalink = (
                f"https://github.com/{repo_row.full_name}/blob/{sha}/{file_row.path}"
                f"#L{file_row.start_line}-L{file_row.end_line}"
            )
            snippet = _build_snippet(file_row.snippet, tokens)
            results.append(
                {
                    "repo": repo_row.full_name,
                    "path": file_row.path,
                    "start_line": file_row.start_line,
                    "end_line": file_row.end_line,
                    "sha": sha,
                    "permalink": permalink,
                    "snippet": snippet,
                    "score": round(score, 3),
                }
            )
        return results

    def search_issues(
        self,
        query: str,
        repo: Optional[str] = None,
        updated_since: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, object]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        stmt = select(GHIssuePR, GHRepo).join(GHRepo, GHIssuePR.repo_id == GHRepo.id)
        if repo:
            stmt = stmt.where(GHRepo.full_name == repo)
        if updated_since:
            cutoff = _parse_datetime(updated_since)
            if cutoff:
                stmt = stmt.where(GHIssuePR.updated_at >= cutoff)
        with session_scope() as session:
            rows = session.execute(stmt).all()
        scored: List[Tuple[float, GHIssuePR, GHRepo]] = []
        for issue_row, repo_row in rows:
            body = issue_row.snippet or ""
            composite = f"{issue_row.title}\n{body}"
            score = _score_text(tokens, composite, repo_row.full_name)
            if score <= 0:
                continue
            scored.append((score, issue_row, repo_row))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: List[Dict[str, object]] = []
        for score, issue_row, repo_row in scored[:top_k]:
            snippet = _build_snippet(issue_row.snippet or issue_row.title, tokens)
            results.append(
                {
                    "number": issue_row.number,
                    "type": issue_row.type,
                    "title": issue_row.title,
                    "state": issue_row.state,
                    "updated": _to_iso(issue_row.updated_at),
                    "url": issue_row.url,
                    "snippet": snippet,
                    "score": round(score, 3),
                }
            )
        return results

    def repo_context(self, repo_full_name: str) -> Dict[str, object]:
        stmt = select(GHRepo).where(GHRepo.full_name == repo_full_name)
        with session_scope() as session:
            repo = session.execute(stmt).scalars().first()
        if repo is None:
            return {"error": "repo not found"}
        languages_data = []
        if isinstance(repo.languages, dict):
            for lang, count in sorted(repo.languages.items(), key=lambda item: item[1], reverse=True):
                languages_data.append({"language": lang, "count": count})
        elif isinstance(repo.languages, list):
            languages_data = repo.languages
        return {
            "languages": languages_data,
            "top_paths": repo.top_paths or [],
            "last_index_at": _to_iso(repo.last_index_at),
        }

    # ------------------------------------------------------------------
    def _exchange_token(self, code: str) -> str:
        if self.mock_enabled:
            return f"mock-token-{code}"
        # In production this would exchange the OAuth code with GitHub.
        # We keep a placeholder implementation for now.
        return f"token-{code}"

    def _fetch_repos(self) -> List[Dict[str, object]]:
        if self.mock_enabled:
            path = self.fixtures_root / "repos.json"
            data = json.loads(path.read_text()) if path.exists() else []
            return data
        return []

    def _upsert_repo(
        self, session, connection: GHConnection, payload: Dict[str, object]
    ) -> GHRepo:
        repo = (
            session.execute(select(GHRepo).where(GHRepo.full_name == payload["full_name"]))
            .scalars()
            .first()
        )
        if repo is None:
            repo = GHRepo(
                connection_id=connection.id,
                name=payload.get("name", payload["full_name"]).split("/")[-1],
                full_name=payload["full_name"],
            )
            session.add(repo)
            session.flush()
        repo.name = payload.get("name", repo.name)
        repo.default_branch = payload.get("default_branch", repo.default_branch)
        repo.private = bool(payload.get("private", False))
        repo.url = payload.get("url") or payload.get("html_url")
        repo.updated_at = _now()
        return repo

    def _run_index_job(self, index_id: str, repo_full_name: str, branch: str, mode: str) -> None:
        self._update_job(index_id, state="running", started_at=_now())
        try:
            repo_info = self._prepare_repo(repo_full_name)
            self._ingest_repo(index_id, repo_info)
            self._update_job(index_id, state="completed", progress=1.0, finished_at=_now())
        except Exception as exc:  # pragma: no cover - defensive
            error_message = f"{exc.__class__.__name__}: {exc}"
            self._update_job(
                index_id,
                state="failed",
                finished_at=_now(),
                errors=[error_message],
            )
            if not isinstance(exc, EXPECTED_INDEX_ERRORS):
                raise

    def _prepare_repo(self, repo_full_name: str) -> Tuple[GHRepo, Path]:
        with session_scope() as session:
            repo = (
                session.execute(select(GHRepo).where(GHRepo.full_name == repo_full_name))
                .scalars()
                .first()
            )
            if repo is None:
                raise ValueError(f"Unknown repository {repo_full_name}")
        if self.mock_enabled:
            repo_path = self.fixtures_root / "repos" / repo_full_name.replace("/", "__")
            if not repo_path.exists():
                raise FileNotFoundError(f"Missing mock repo fixture for {repo_full_name}")
            return repo, repo_path
        raise RuntimeError("Non-mock GitHub indexing is not implemented in this environment")

    def _ingest_repo(self, index_id: str, repo_info: Tuple[GHRepo, Path]) -> None:
        repo, repo_path = repo_info
        files: List[Path] = [p for p in repo_path.rglob("*") if p.is_file()]
        total = len(files) or 1
        language_counter: Counter[str] = Counter()
        path_counter: Counter[str] = Counter()
        file_rows: List[Dict[str, object]] = []
        for idx, file_path in enumerate(files, start=1):
            data = file_path.read_bytes()
            if len(data) > MAX_FILE_SIZE_BYTES:
                self._update_progress(index_id, idx, total)
                continue
            if b"\0" in data:
                self._update_progress(index_id, idx, total)
                continue
            text = data.decode("utf-8", errors="ignore")
            rel_path = str(file_path.relative_to(repo_path))
            for lang in iter_language_from_path(rel_path):
                language_counter[lang] += 1
            parent = file_path.parent.relative_to(repo_path)
            path_counter[str(parent) or "."] += 1
            for chunk in chunk_source(rel_path, text):
                file_rows.append(
                    {
                        "path": chunk.path,
                        "start": chunk.start_line,
                        "end": chunk.end_line,
                        "snippet": chunk.text,
                        "sha": uuid.uuid5(uuid.NAMESPACE_URL, f"{rel_path}:{chunk.start_line}:{chunk.end_line}").hex,
                    }
                )
            self._update_progress(index_id, idx, total)

        with session_scope() as session:
            repo_db = session.get(GHRepo, repo.id)
            if repo_db is None:
                raise ValueError("Repository disappeared during indexing")
            session.query(GHFile).filter(GHFile.repo_id == repo.id).delete(synchronize_session=False)
            for row in file_rows:
                gh_file = GHFile(
                    repo_id=repo.id,
                    path=row["path"],
                    start_line=row["start"],
                    end_line=row["end"],
                    snippet=row["snippet"],
                    sha=row["sha"],
                )
                session.add(gh_file)

            issues_payload = self._load_issues(repo_db.full_name)
            session.query(GHIssuePR).filter(GHIssuePR.repo_id == repo.id).delete(
                synchronize_session=False
            )
            for payload in issues_payload:
                issue = GHIssuePR(
                    repo_id=repo.id,
                    number=payload["number"],
                    type=payload.get("type", "issue"),
                    title=payload.get("title", ""),
                    state=payload.get("state"),
                    updated_at=_parse_datetime(payload.get("updated_at")),
                    url=payload.get("url"),
                    snippet=payload.get("body", "")[:MAX_SNIPPET_LENGTH],
                )
                session.add(issue)

            repo_db.languages = dict(language_counter)
            repo_db.top_paths = [path for path, _ in path_counter.most_common(5)]
            repo_db.last_index_at = _now()
            repo_db.head_sha = uuid.uuid5(uuid.NAMESPACE_URL, repo_db.full_name).hex

    def _load_issues(self, repo_full_name: str) -> List[Dict[str, object]]:
        if not self.mock_enabled:
            return []
        issues_dir = self.fixtures_root / "issues"
        path = issues_dir / f"{repo_full_name.replace('/', '__')}.json"
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def _update_progress(self, index_id: str, processed: int, total: int) -> None:
        progress = min(max(processed / float(total), 0.0), 1.0)
        self._update_job(index_id, progress=progress, processed_items=processed, total_items=total)

    def _update_job(self, index_id: str, **updates) -> None:
        with self._lock:
            job = self._jobs.get(index_id)
            if not job:
                return
            for key, value in updates.items():
                setattr(job, key, value)


github_integration_service = GitHubIntegrationService()

__all__ = ["GitHubIntegrationService", "github_integration_service"]

