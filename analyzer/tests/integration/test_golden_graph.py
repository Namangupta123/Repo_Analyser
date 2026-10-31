import json
from pathlib import Path

from repo_analyzer import analyze_repository


FIXTURE = Path(__file__).parents[1] / "fixtures" / "react_fastapi_project"


def _local_pairs(result: object) -> set[tuple[str, str]]:
    paths = {node.id: node.path for node in result.nodes if node.path is not None}  # type: ignore[attr-defined]
    return {
        (paths[edge.source], paths[edge.target])
        for edge in result.edges  # type: ignore[attr-defined]
        if edge.relationship_type == "IMPORTS"
    }


def test_react_fastapi_golden_graph(tmp_path: Path) -> None:
    result = analyze_repository(str(FIXTURE), tmp_path / "analysis")
    pairs = _local_pairs(result)
    assert ("frontend/src/App.tsx", "frontend/src/pages/Orders.tsx") in pairs
    assert ("frontend/src/pages/Orders.tsx", "frontend/src/api/orders.ts") in pairs
    assert ("frontend/src/pages/Orders.tsx", "frontend/src/components/OrderCard.tsx") in pairs
    assert ("backend/app/main.py", "backend/app/routes/orders.py") in pairs
    assert ("backend/app/routes/orders.py", "backend/app/services/order_service.py") in pairs
    assert ("backend/app/services/order_service.py", "backend/app/database/postgres.py") in pairs
    assert result.metrics.imports_unresolved == 0
    assert all(edge.confidence == 1.0 and edge.evidence.module for edge in result.edges)


def test_output_envelopes_and_external_namespaces(tmp_path: Path) -> None:
    output = tmp_path / "analysis"
    result = analyze_repository(str(FIXTURE), output)
    graph = json.loads((output / "graph.json").read_text(encoding="utf-8"))
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    errors = json.loads((output / "errors.json").read_text(encoding="utf-8"))
    assert graph["schema_version"] == report["schema_version"] == errors["schema_version"] == "1.0.0"
    ecosystems = {node["metadata"].get("ecosystem") for node in graph["nodes"] if node["type"] == "external_package"}
    assert {"npm", "python", "python-stdlib"} >= ecosystems
    assert report["status"] == result.status
    assert errors["unresolved"] == []


def test_graph_ids_are_deterministic(tmp_path: Path) -> None:
    first = analyze_repository(str(FIXTURE), tmp_path / "first")
    second = analyze_repository(str(FIXTURE), tmp_path / "second")
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.edges] == [edge.id for edge in second.edges]


def test_unresolved_and_malformed_files_degrade_gracefully(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "good.py").write_text("import definitely_missing_package\n", encoding="utf-8")
    (repository / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    result = analyze_repository(str(repository), tmp_path / "out")
    assert result.status == "PARTIAL_SUCCESS"
    assert result.metrics.files_failed == 1
    assert result.metrics.imports_unresolved == 1
    assert not result.edges
    assert result.unresolved[0].reason == "MODULE_NOT_FOUND"

