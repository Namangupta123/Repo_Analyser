from pathlib import Path

from repo_analyzer import __version__, analyze_repository
from repo_analyzer.config import DEFAULT_IGNORE_DIRS
from repo_analyzer.core.models import GraphNode, ImportEvidence, ImportFact


def test_public_package_contract() -> None:
    assert __version__ == "0.1.0"
    assert callable(analyze_repository)
    assert {".git", "node_modules", ".venv"} <= DEFAULT_IGNORE_DIRS


def test_models_do_not_share_mutable_defaults() -> None:
    first = ImportFact(source_file="a.py", module="x", evidence=ImportEvidence(module="x", line=1, column=1))
    second = ImportFact(source_file="b.py", module="y", evidence=ImportEvidence(module="y", line=1, column=1))
    first.symbols.append("changed")
    assert second.symbols == []

    node_a = GraphNode(id="a", type="file", name="a")
    node_b = GraphNode(id="b", type="file", name="b")
    node_a.metadata["changed"] = True
    assert node_b.metadata == {}


def test_local_analysis_writes_default_contract(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "a.py").write_text("import os\n", encoding="utf-8")
    output = tmp_path / "out"
    result = analyze_repository(str(repository), output)
    assert result.status == "COMPLETED"
    assert {path.name for path in output.iterdir()} == {"graph.json", "report.json", "errors.json"}

