from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class AliasRule:
    config_root: str
    pattern: str
    targets: tuple[str, ...]
    base_url: str


class TypeScriptAliases:
    def __init__(self, rules: list[AliasRule] | None = None) -> None:
        self.rules = rules or []

    @classmethod
    def load(cls, root: Path, config_files: list[str]) -> TypeScriptAliases:
        rules: list[AliasRule] = []
        for relative in config_files:
            if PurePosixPath(relative).name != "tsconfig.json":
                continue
            try:
                payload = json.loads(_strip_jsonc((root / relative).read_text(encoding="utf-8")))
                options = payload.get("compilerOptions", {})
                paths = options.get("paths", {})
                config_root = str(PurePosixPath(relative).parent)
                if config_root == ".":
                    config_root = ""
                base_url = str(options.get("baseUrl", "."))
                for pattern, targets in paths.items():
                    if isinstance(pattern, str) and isinstance(targets, list):
                        clean_targets = tuple(value for value in targets if isinstance(value, str))
                        if clean_targets:
                            rules.append(AliasRule(config_root, pattern, clean_targets, base_url))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                continue
        rules.sort(key=lambda rule: len(rule.config_root), reverse=True)
        return cls(rules)

    def candidates(self, module: str, source_path: str) -> list[str]:
        candidates: list[str] = []
        for rule in self.rules:
            if rule.config_root and not source_path.startswith(rule.config_root + "/"):
                continue
            replacement = self._match(rule.pattern, module)
            if replacement is None:
                continue
            for target in rule.targets:
                expanded = target.replace("*", replacement)
                candidates.append(posixpath.normpath(posixpath.join(rule.config_root, rule.base_url, expanded)))
        return candidates

    @staticmethod
    def _match(pattern: str, module: str) -> str | None:
        if "*" not in pattern:
            return "" if pattern == module else None
        prefix, suffix = pattern.split("*", 1)
        if not module.startswith(prefix) or not module.endswith(suffix):
            return None
        end = len(module) - len(suffix) if suffix else len(module)
        return module[len(prefix):end]


def _strip_jsonc(value: str) -> str:
    """Remove JSON comments and trailing commas without changing quoted strings."""
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(value):
        character = value[index]
        next_character = value[index + 1] if index + 1 < len(value) else ""
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if character == "/" and next_character == "/":
            index += 2
            while index < len(value) and value[index] not in "\r\n":
                index += 1
            continue
        if character == "/" and next_character == "*":
            index += 2
            while index + 1 < len(value) and value[index:index + 2] != "*/":
                index += 1
            index += 2
            continue
        if character == ",":
            lookahead = index + 1
            while lookahead < len(value) and value[lookahead].isspace():
                lookahead += 1
            if lookahead < len(value) and value[lookahead] in "}]":
                index += 1
                continue
        output.append(character)
        index += 1
    return "".join(output)

