import pytest

from repo_analyzer.extractors import extract_imports
from repo_analyzer.parsers import JavaScriptParser, PythonParser


def test_python_ast_import_extraction() -> None:
    parsed = PythonParser().parse("app/routes.py", "import os\nfrom .services import create_order\n")
    facts = extract_imports(parsed)
    assert [(fact.module, fact.symbols, fact.relative_level) for fact in facts] == [
        ("os", ["os"], 0),
        ("services", ["create_order"], 1),
    ]
    assert facts[1].evidence.line == 2


@pytest.mark.parametrize("path,text", [
    ("app.js", 'const x = require("x");'),
    ("app.jsx", 'import Card from "./Card"; const x = <Card />;'),
    ("app.ts", 'export { value } from "./value";'),
    ("app.tsx", 'import React from "react"; const x: JSX.Element = <div />;'),
])
def test_tree_sitter_supported_syntax(path: str, text: str) -> None:
    facts = extract_imports(JavaScriptParser().parse(path, text))
    assert len(facts) == 1


def test_dynamic_import_is_marked() -> None:
    fact = extract_imports(JavaScriptParser().parse("app.ts", 'const x = import("./lazy");'))[0]
    assert fact.module == "./lazy"
    assert fact.is_dynamic is True


@pytest.mark.parametrize("parser,path,text", [
    (PythonParser(), "bad.py", "def broken(:\n"),
    (JavaScriptParser(), "bad.tsx", "const broken: = ;"),
])
def test_malformed_source_raises_syntax_error(parser: object, path: str, text: str) -> None:
    with pytest.raises(SyntaxError):
        parser.parse(path, text)  # type: ignore[attr-defined]

