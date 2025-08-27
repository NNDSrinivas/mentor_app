import os
import sys

sys.path.append(os.getcwd())

from backend.patch_suggester import suggest_patch


def test_suggest_patch_missing_dependency():
    log = "ModuleNotFoundError: No module named 'samplepkg'"
    patch = suggest_patch(log)
    assert 'requirements.txt' in patch
    assert 'samplepkg' in patch


def test_suggest_patch_assertion_mismatch():
    log = (
        ">       assert add(1,2) == 4\n"
        "E       AssertionError: assert 3 == 4\n\n"
        "tests/test_math.py:5: AssertionError"
    )
    patch = suggest_patch(log)
    assert 'tests/test_math.py' in patch
    assert '+assert 3 == 4' in patch
