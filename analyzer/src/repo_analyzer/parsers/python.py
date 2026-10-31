from __future__ import annotations

import ast
import sys

from .base import ParsedSource


class PythonParser:
    def parse(self, path: str, text: str) -> ParsedSource:
        tree = ast.parse(text, filename=path, type_comments=True)
        return ParsedSource(
            path=path,
            text=text,
            language="python",
            tree=tree,
            parser_version=f"python-ast-{sys.version_info.major}.{sys.version_info.minor}",
        )

