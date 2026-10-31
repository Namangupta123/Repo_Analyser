import json
from pathlib import Path

from repo_analyzer.cli import main


def test_cli_writes_outputs_and_progress(tmp_path: Path, capsys: object) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "main.py").write_text("import os\n", encoding="utf-8")
    output = tmp_path / "out"
    assert main([str(repository), "--output", str(output)]) == 0
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "[1/7]" in captured and "[7/7]" in captured
    assert "Status: COMPLETED" in captured
    assert json.loads((output / "report.json").read_text())["metrics"]["imports_resolved"] == 1

