from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.watchers import ci_watcher


def test_ci_watcher_enqueues_patch(monkeypatch):
    sample_patch = """--- a/foo.txt\n+++ b/foo.txt\n@@\n-old\n+new\n"""
    submitted = []

    class DummyApprovals:
        def submit(self, action, payload):
            submitted.append((action, payload))
            class Item:
                id = '1'
            return Item()

    monkeypatch.setattr(ci_watcher, 'get_approvals', lambda: DummyApprovals())

    class DummyMonitor:
        def monitor_repository(self, repo, branch):
            return {'recent_failures': [{'analysis': {'proposed_patch': sample_patch}}]}

    monkeypatch.setattr(ci_watcher, 'BuildMonitor', lambda: DummyMonitor())

    payload = {
        'action': 'completed',
        'check_suite': {
            'conclusion': 'failure',
            'head_branch': 'main',
            'id': 1,
            'head_sha': 'abc',
            'pull_requests': [{'number': 1, 'title': 't'}],
        },
        'repository': {'full_name': 'owner/repo'},
    }

    ci_watcher.handle_check_suite(payload)

    actions = [a for a, _ in submitted]
    assert 'github.apply_patch' in actions
    patch_payload = next(p for a, p in submitted if a == 'github.apply_patch')
    expected = ci_watcher.compute_minimal_patch(sample_patch)
    assert patch_payload['patch_content'].strip() == expected.strip()
