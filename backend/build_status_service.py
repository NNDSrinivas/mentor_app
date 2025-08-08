from __future__ import annotations
import os
import time
import threading
import logging
from typing import Dict, Any
import requests
import subprocess

from app.realtime import broadcast_event

log = logging.getLogger(__name__)


class BuildStatusService:
    """Polls GitHub/GitLab build APIs and notifies on status changes."""

    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self.running = False
        self.thread: threading.Thread | None = None
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.gitlab_token = os.getenv("GITLAB_TOKEN", "")
        self.github_repo = os.getenv("GITHUB_REPO")  # e.g. owner/repo
        self.gitlab_project = os.getenv("GITLAB_PROJECT")  # numeric project id
        self._last_status: Dict[str, str] = {}

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        log.info("BuildStatusService started")

    def stop(self):
        self.running = False

    def _run(self):
        while self.running:
            try:
                if self.github_repo:
                    self._check_github()
                if self.gitlab_project:
                    self._check_gitlab()
            except Exception as e:
                log.error(f"Build status polling error: {e}")
            time.sleep(self.poll_interval)

    # --- GitHub ---
    def _gh_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _check_github(self):
        owner, repo = self.github_repo.split("/")
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=self._gh_headers(),
        )
        r.raise_for_status()
        for pr in r.json():
            sha = pr.get("head", {}).get("sha")
            if not sha:
                continue
            status_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/status",
                headers=self._gh_headers(),
            )
            status_resp.raise_for_status()
            state = status_resp.json().get("state")
            key = f"github:{pr['number']}"
            if state and self._last_status.get(key) != state:
                self._last_status[key] = state
                self._handle_status(
                    source="github",
                    pr_number=pr["number"],
                    status=state,
                    title=pr.get("title"),
                    url=pr.get("html_url"),
                )

    # --- GitLab ---
    def _gl_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.gitlab_token:
            headers["PRIVATE-TOKEN"] = self.gitlab_token
        return headers

    def _check_gitlab(self):
        project = self.gitlab_project
        r = requests.get(
            f"https://gitlab.com/api/v4/projects/{project}/merge_requests?state=opened",
            headers=self._gl_headers(),
        )
        r.raise_for_status()
        for mr in r.json():
            iid = mr.get("iid")
            if iid is None:
                continue
            pipes = requests.get(
                f"https://gitlab.com/api/v4/projects/{project}/merge_requests/{iid}/pipelines",
                headers=self._gl_headers(),
            )
            pipes.raise_for_status()
            if not pipes.json():
                continue
            latest = pipes.json()[0]
            status = latest.get("status")
            key = f"gitlab:{iid}"
            if status and self._last_status.get(key) != status:
                self._last_status[key] = status
                self._handle_status(
                    source="gitlab",
                    pr_number=iid,
                    status=status,
                    title=mr.get("title"),
                    url=mr.get("web_url"),
                )

    # --- handling ---
    def _handle_status(self, source: str, pr_number: int, status: str, title: str | None, url: str | None):
        info: Dict[str, Any] = {
            "source": source,
            "pr_number": pr_number,
            "status": status,
            "title": title,
            "url": url,
        }
        broadcast_event("build_status", info)
        log.info(f"Build status changed: {info}")
        if status.lower() in ("failure", "failed"):
            self._rerun_tests()

    def _rerun_tests(self):
        try:
            log.info("Re-running tests due to build failure")
            subprocess.run(["pytest"], check=False)
        except Exception as e:
            log.error(f"Failed to run tests: {e}")
