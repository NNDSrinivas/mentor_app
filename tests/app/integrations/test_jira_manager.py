import os
import sys
from unittest.mock import Mock
import requests
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from backend.integrations import jira_manager


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr(jira_manager, "JIRA_BASE", "https://example.atlassian.net")
    monkeypatch.setattr(jira_manager, "JIRA_USER", "user@example.com")
    monkeypatch.setattr(jira_manager, "JIRA_TOKEN", "token")
    return jira_manager.JiraManager(dry_run=False)


def test_get_assigned_issues_success(manager, monkeypatch):
    mock_resp = Mock()
    mock_resp.json.return_value = {"issues": [{"key": "TASK-1"}]}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(jira_manager.requests, "get", Mock(return_value=mock_resp))
    result = manager.get_assigned_issues("user@example.com")
    assert result == {"issues": [{"key": "TASK-1"}]}


def test_get_assigned_issues_http_error(manager, monkeypatch):
    monkeypatch.setattr(jira_manager.requests, "get", Mock(side_effect=requests.HTTPError("boom")))
    with pytest.raises(requests.HTTPError):
        manager.get_assigned_issues("user@example.com")


def test_get_assigned_issues_missing_credentials(monkeypatch):
    monkeypatch.setattr(jira_manager, "JIRA_BASE", "https://example.atlassian.net")
    monkeypatch.setattr(jira_manager, "JIRA_USER", "")
    monkeypatch.setattr(jira_manager, "JIRA_TOKEN", "")
    mgr = jira_manager.JiraManager(dry_run=False)
    monkeypatch.setattr(jira_manager.requests, "get", Mock(side_effect=requests.HTTPError("401")))
    with pytest.raises(requests.HTTPError):
        mgr.get_assigned_issues("user@example.com")


def test_add_comment_success(manager, monkeypatch):
    mock_resp = Mock()
    mock_resp.json.return_value = {"id": "1"}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(jira_manager.requests, "post", Mock(return_value=mock_resp))
    result = manager.add_comment("TASK-1", "hello")
    assert result == {"id": "1"}


def test_add_comment_http_error(manager, monkeypatch):
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("fail")))
    with pytest.raises(requests.HTTPError):
        manager.add_comment("TASK-1", "hello")


def test_add_comment_missing_credentials(monkeypatch):
    monkeypatch.setattr(jira_manager, "JIRA_BASE", "https://example.atlassian.net")
    monkeypatch.setattr(jira_manager, "JIRA_USER", "")
    monkeypatch.setattr(jira_manager, "JIRA_TOKEN", "")
    mgr = jira_manager.JiraManager(dry_run=False)
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("401")))
    with pytest.raises(requests.HTTPError):
        mgr.add_comment("TASK-1", "hello")


def test_transition_issue_success(manager, monkeypatch):
    mock_resp = Mock()
    mock_resp.json.return_value = {"ok": True}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(jira_manager.requests, "post", Mock(return_value=mock_resp))
    result = manager.transition_issue("TASK-1", "2", comment="done")
    assert result == {"ok": True}


def test_transition_issue_http_error(manager, monkeypatch):
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("bad")))
    with pytest.raises(requests.HTTPError):
        manager.transition_issue("TASK-1", "2")


def test_transition_issue_missing_credentials(monkeypatch):
    monkeypatch.setattr(jira_manager, "JIRA_BASE", "https://example.atlassian.net")
    monkeypatch.setattr(jira_manager, "JIRA_USER", "")
    monkeypatch.setattr(jira_manager, "JIRA_TOKEN", "")
    mgr = jira_manager.JiraManager(dry_run=False)
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("401")))
    with pytest.raises(requests.HTTPError):
        mgr.transition_issue("TASK-1", "2")


def test_create_issue_success(manager, monkeypatch):
    mock_resp = Mock()
    mock_resp.json.return_value = {"key": "TASK-1"}
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(jira_manager.requests, "post", Mock(return_value=mock_resp))
    result = manager.create_issue("PRJ", "summary", "desc")
    assert result == {"key": "TASK-1"}


def test_create_issue_http_error(manager, monkeypatch):
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("bad")))
    with pytest.raises(requests.HTTPError):
        manager.create_issue("PRJ", "summary", "desc")


def test_create_issue_missing_credentials(monkeypatch):
    monkeypatch.setattr(jira_manager, "JIRA_BASE", "https://example.atlassian.net")
    monkeypatch.setattr(jira_manager, "JIRA_USER", "")
    monkeypatch.setattr(jira_manager, "JIRA_TOKEN", "")
    mgr = jira_manager.JiraManager(dry_run=False)
    monkeypatch.setattr(jira_manager.requests, "post", Mock(side_effect=requests.HTTPError("401")))
    with pytest.raises(requests.HTTPError):
        mgr.create_issue("PRJ", "summary", "desc")

