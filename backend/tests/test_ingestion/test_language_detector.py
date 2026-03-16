from pathlib import Path
import pytest
from app.ingestion.language_detector import detect_languages, EXTENSION_MAP

def test_java_detected(tmp_path):
    (tmp_path / "Main.java").write_text("class Main {}")
    langs = detect_languages(tmp_path)
    assert "java" in langs

def test_typescript_detected(tmp_path):
    (tmp_path / "app.ts").write_text("const x: number = 1;")
    langs = detect_languages(tmp_path)
    assert "typescript" in langs

def test_tsx_maps_to_typescript(tmp_path):
    (tmp_path / "App.tsx").write_text("export default function App() {}")
    langs = detect_languages(tmp_path)
    assert "typescript" in langs

def test_multiple_languages(tmp_path):
    (tmp_path / "Main.java").write_text("")
    (tmp_path / "main.go").write_text("")
    (tmp_path / "lib.rs").write_text("")
    langs = detect_languages(tmp_path)
    assert set(langs) == {"java", "go", "rust"}

def test_unknown_extensions_ignored(tmp_path):
    (tmp_path / "README.md").write_text("")
    (tmp_path / ".gitignore").write_text("")
    langs = detect_languages(tmp_path)
    assert langs == []

def test_nested_files_detected(tmp_path):
    sub = tmp_path / "src" / "main"
    sub.mkdir(parents=True)
    (sub / "App.kt").write_text("")
    langs = detect_languages(tmp_path)
    assert "kotlin" in langs

def test_extension_map_completeness():
    required = {".java", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".kt", ".kts", ".rb", ".c", ".h"}
    assert required.issubset(set(EXTENSION_MAP.keys()))
