from __future__ import annotations

from tree_sitter import Language, Parser
import tree_sitter_javascript
import tree_sitter_typescript

from .base import ParsedSource


class JavaScriptParser:
    def __init__(self) -> None:
        self._languages = {
            ".js": Language(tree_sitter_javascript.language()),
            ".jsx": Language(tree_sitter_javascript.language()),
            ".ts": Language(tree_sitter_typescript.language_typescript()),
            ".tsx": Language(tree_sitter_typescript.language_tsx()),
        }

    def parse(self, path: str, text: str) -> ParsedSource:
        extension = "." + path.rsplit(".", 1)[-1].lower()
        language = self._languages[extension]
        tree = Parser(language).parse(text.encode("utf-8"))
        if tree.root_node.has_error:
            raise SyntaxError(f"Tree-sitter reported invalid syntax in {path}")
        return ParsedSource(
            path=path,
            text=text,
            language="typescript" if extension in {".ts", ".tsx"} else "javascript",
            tree=tree,
            parser_version="tree-sitter-0.25",
        )

