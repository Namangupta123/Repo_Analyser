from pathlib import Path

from repo_analyzer import analyze_repository


def _pairs(result: object) -> set[tuple[str, str]]:
    paths = {node.id: node.path for node in result.nodes if node.path}  # type: ignore[attr-defined]
    return {
        (paths[edge.source], paths[edge.target])
        for edge in result.edges  # type: ignore[attr-defined]
        if edge.relationship_type == "IMPORTS"
    }


def test_index_modules_and_circular_dependencies(tmp_path: Path) -> None:
    (tmp_path / "orders").mkdir()
    (tmp_path / "orders" / "index.ts").write_text('import "../a";\n', encoding="utf-8")
    (tmp_path / "a.ts").write_text('import orders from "./orders";\n', encoding="utf-8")
    result = analyze_repository(str(tmp_path), tmp_path / "out")
    assert _pairs(result) == {
        ("a.ts", "orders/index.ts"),
        ("orders/index.ts", "a.ts"),
    }


def test_python_relative_import(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "main.py").write_text("from .helpers import value\n", encoding="utf-8")
    (package / "helpers.py").write_text("value = 1\n", encoding="utf-8")
    result = analyze_repository(str(tmp_path), tmp_path / "out")
    assert ("package/main.py", "package/helpers.py") in _pairs(result)


def test_dynamic_import_is_unresolved_without_an_edge(tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text('const lazy = import("./lazy");\n', encoding="utf-8")
    (tmp_path / "lazy.ts").write_text("export {};\n", encoding="utf-8")
    result = analyze_repository(str(tmp_path), tmp_path / "out")
    assert result.metrics.imports_unresolved == 1
    assert result.unresolved[0].reason == "DYNAMIC_IMPORT"
    assert result.edges == []


def test_jsonc_typescript_alias_is_local_not_external(tmp_path: Path) -> None:
    (tmp_path / "src" / "components").mkdir(parents=True)
    (tmp_path / "src" / "main.ts").write_text('import Button from "@/components/Button";\n', encoding="utf-8")
    (tmp_path / "src" / "components" / "Button.tsx").write_text("export default function Button() { return <button />; }\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": { /* bundler settings */ "paths": {"@/*": ["./src/*",],},}}',
        encoding="utf-8",
    )
    result = analyze_repository(str(tmp_path), tmp_path / "out")
    assert ("src/main.ts", "src/components/Button.tsx") in _pairs(result)
    assert not any(node.name == "@/components" for node in result.nodes)


def test_python_dependency_groups_and_known_distribution_aliases(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("import typer\nimport jwt\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["pyjwt>=2"]\n[dependency-groups]\ndev = ["typer>=0.27"]\n',
        encoding="utf-8",
    )
    result = analyze_repository(str(tmp_path), tmp_path / "out")
    external = {(node.metadata.get("ecosystem"), node.name) for node in result.nodes if node.type == "external_package"}
    assert {("python", "jwt"), ("python", "typer")} <= external
    assert result.metrics.imports_unresolved == 0
