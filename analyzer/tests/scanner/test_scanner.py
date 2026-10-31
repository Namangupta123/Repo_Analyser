from pathlib import Path

from repo_analyzer.config import AnalyzerConfig
from repo_analyzer.scanner import RepositoryScanner


def test_scans_hashes_and_ignores_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("export {};", encoding="utf-8")
    result = RepositoryScanner().scan(tmp_path)
    assert [item.relative_path for item in result.files] == ["src/a.py"]
    assert len(result.files[0].content_hash) == 64
    assert result.config_files == ["package.json"]


def test_skips_binary_huge_and_symlink_files(tmp_path: Path) -> None:
    (tmp_path / "binary.py").write_bytes(b"\x00not-source")
    (tmp_path / "huge.ts").write_text("x" * 21, encoding="utf-8")
    outside = tmp_path.parent / "outside.js"
    outside.write_text("export {};", encoding="utf-8")
    (tmp_path / "linked.js").symlink_to(outside)
    result = RepositoryScanner(AnalyzerConfig(max_file_size_bytes=20)).scan(tmp_path)
    assert result.files == []
    assert {error.error_type for error in result.errors} == {"BINARY_FILE", "FILE_TOO_LARGE", "UNSAFE_SYMLINK"}

