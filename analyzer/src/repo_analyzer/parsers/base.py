from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ParsedSource:
    path: str
    text: str
    language: str
    tree: Any
    parser_version: str


class SourceParser(Protocol):
    def parse(self, path: str, text: str) -> ParsedSource: ...

