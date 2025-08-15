from pathlib import Path
import sys
from dataclasses import dataclass

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.codegen import generate_code_and_tests


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    status: str


def test_generate_code_and_tests(tmp_path: Path) -> None:
    task = Task(task_id="123", title="Sample", description="demo", status="todo")

    paths = generate_code_and_tests(task, tmp_path, tmp_path)

    src = Path(paths["source"])
    test = Path(paths["test"])

    assert src.exists()
    assert test.exists()

    assert "demo" in src.read_text()
    assert "test_placeholder" in test.read_text()
