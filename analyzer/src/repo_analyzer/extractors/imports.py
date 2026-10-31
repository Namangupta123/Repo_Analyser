from __future__ import annotations

import ast
from collections.abc import Iterator
from typing import Any

from repo_analyzer.core.models import ImportEvidence, ImportFact
from repo_analyzer.parsers.base import ParsedSource


def extract_imports(parsed: ParsedSource) -> list[ImportFact]:
    if parsed.language == "python":
        return _extract_python(parsed)
    return _extract_javascript(parsed)


def _extract_python(parsed: ParsedSource) -> list[ImportFact]:
    facts: list[ImportFact] = []
    for node in ast.walk(parsed.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                facts.append(_fact(
                    parsed.path,
                    alias.name,
                    [alias.asname or alias.name],
                    node.lineno,
                    node.col_offset + 1,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            facts.append(_fact(
                parsed.path,
                module,
                [alias.name for alias in node.names],
                node.lineno,
                node.col_offset + 1,
                relative_level=node.level,
                is_from_import=True,
            ))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            module = _python_string_argument(node)
            facts.append(_fact(
                parsed.path,
                module,
                [],
                node.lineno,
                node.col_offset + 1,
                is_dynamic=True,
            ))
    return sorted(facts, key=lambda item: (item.evidence.line, item.evidence.column, item.module))


def _python_string_argument(node: ast.Call) -> str:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return "<dynamic>"


def _extract_javascript(parsed: ParsedSource) -> list[ImportFact]:
    source = parsed.text.encode("utf-8")
    facts: list[ImportFact] = []
    for node in _walk(parsed.tree.root_node):
        if node.type in {"import_statement", "export_statement"}:
            source_node = node.child_by_field_name("source")
            if source_node is None:
                continue
            module = _string_value(source_node, source)
            symbols = _import_symbols(node, source_node, source)
            row, column = node.start_point
            facts.append(_fact(parsed.path, module, symbols, row + 1, column + 1))
        elif node.type == "call_expression":
            function = node.child_by_field_name("function")
            arguments = node.child_by_field_name("arguments")
            if function is None or arguments is None:
                continue
            function_text = _node_text(function, source)
            if function_text not in {"require", "import"} and function.type != "import":
                continue
            argument = next((child for child in arguments.named_children), None)
            module = _string_value(argument, source) if argument is not None and argument.type in {"string", "template_string"} else "<dynamic>"
            row, column = node.start_point
            facts.append(_fact(
                parsed.path,
                module,
                [],
                row + 1,
                column + 1,
                is_dynamic=function_text == "import" or function.type == "import" or module == "<dynamic>",
            ))
    unique: dict[tuple[int, int, str, bool], ImportFact] = {}
    for fact in facts:
        unique[(fact.evidence.line, fact.evidence.column, fact.module, fact.is_dynamic)] = fact
    return sorted(unique.values(), key=lambda item: (item.evidence.line, item.evidence.column, item.module))


def _walk(node: Any) -> Iterator[Any]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _import_symbols(node: Any, source_node: Any, source: bytes) -> list[str]:
    symbols: list[str] = []
    for descendant in _walk(node):
        if descendant == source_node:
            continue
        if descendant.type in {"identifier", "property_identifier"}:
            value = _node_text(descendant, source)
            if value not in symbols:
                symbols.append(value)
    return symbols


def _node_text(node: Any, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8")


def _string_value(node: Any, source: bytes) -> str:
    value = _node_text(node, source)
    if len(value) >= 2 and value[0] in {'"', "'", "`"} and value[-1] == value[0]:
        return value[1:-1]
    return value


def _fact(
    source_file: str,
    module: str,
    symbols: list[str],
    line: int,
    column: int,
    *,
    relative_level: int = 0,
    is_from_import: bool = False,
    is_dynamic: bool = False,
) -> ImportFact:
    return ImportFact(
        source_file=source_file,
        module=module,
        symbols=symbols,
        relative_level=relative_level,
        is_from_import=is_from_import,
        is_dynamic=is_dynamic,
        evidence=ImportEvidence(module=module, line=line, column=column),
    )

