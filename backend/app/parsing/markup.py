"""Parsers for non-code files: XML/pom.xml, package.json, Markdown, YAML, HTML."""
from __future__ import annotations
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from .base import BaseParser, ParsedFile, ImportDef, ConstantDef


# ── helpers ──────────────────────────────────────────────────────────────────

def _stub(file_path: str, language: str) -> ParsedFile:
    return ParsedFile(
        file_path=file_path, language=language,
        classes=[], functions=[], imports=[], constants=[], config_values=[],
    )


# ── XML / pom.xml ─────────────────────────────────────────────────────────────

_MVN = "http://maven.apache.org/POM/4.0.0"


def _mvn(tag: str) -> str:
    return f"{{{_MVN}}}{tag}"


def _text(el, tag: str, ns: str = "") -> str:
    t = el.find(f"{{{ns}}}{tag}" if ns else tag)
    return t.text.strip() if t is not None and t.text else ""


class PomXmlParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        pf = _stub(file_path, "xml")
        try:
            root = ET.fromstring(source_code)
            ns = _MVN if root.tag.startswith(f"{{{_MVN}}}") else ""
            group_id   = _text(root, "groupId",    ns) or _text(root, "groupId")
            artifact_id = _text(root, "artifactId", ns) or _text(root, "artifactId")
            version    = _text(root, "version",    ns) or _text(root, "version")
            if group_id:
                pf.package = group_id
            # Emit project coordinates as constants
            line = 1
            for key, val in [("groupId", group_id), ("artifactId", artifact_id), ("version", version)]:
                if val:
                    pf.constants.append(ConstantDef(name=key, value=val, line=line, var_kind="constant"))
                    line += 1
            # Dependencies as imports
            deps_tag = f"{{{ns}}}dependencies" if ns else "dependencies"
            dep_tag  = f"{{{ns}}}dependency"   if ns else "dependency"
            deps = root.find(deps_tag)
            if deps is None:
                # try without NS
                deps = root.find("dependencies")
                dep_tag = "dependency"
            if deps is not None:
                for dep in deps.findall(dep_tag):
                    g = _text(dep, "groupId",    ns) or _text(dep, "groupId")
                    a = _text(dep, "artifactId", ns) or _text(dep, "artifactId")
                    v = _text(dep, "version",    ns) or _text(dep, "version")
                    if g and a:
                        coord = f"{g}:{a}" + (f":{v}" if v else "")
                        pf.imports.append(ImportDef(
                            source=coord, resolved_file=None, bindings=[], is_reexport=False,
                        ))
        except ET.ParseError:
            pass
        return pf


class GenericXmlParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        # Delegate to pom.xml parser for Maven files, otherwise just file node
        name = Path(file_path).name
        if name == "pom.xml":
            return PomXmlParser().parse(file_path, source_code)
        pf = _stub(file_path, "xml")
        try:
            root = ET.fromstring(source_code)
            # Capture root element and up to 5 top-level child tag names as constants
            pf.constants.append(ConstantDef(name="rootElement", value=root.tag.split("}")[-1], line=1, var_kind="constant"))
        except ET.ParseError:
            pass
        return pf


# ── package.json ──────────────────────────────────────────────────────────────

class PackageJsonParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        pf = _stub(file_path, "json")
        try:
            data = json.loads(source_code)
            name    = data.get("name", "")
            version = data.get("version", "")
            if name:
                pf.package = name
            for key, val in [("name", name), ("version", version)]:
                if val:
                    pf.constants.append(ConstantDef(name=key, value=val, line=1, var_kind="constant"))
            for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
                for pkg, ver in data.get(dep_key, {}).items():
                    pf.imports.append(ImportDef(
                        source=f"{pkg}@{ver}", resolved_file=None, bindings=[], is_reexport=False,
                    ))
        except (json.JSONDecodeError, AttributeError):
            pass
        return pf


class GenericJsonParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        name = Path(file_path).name
        if name == "package.json":
            return PackageJsonParser().parse(file_path, source_code)
        pf = _stub(file_path, "json")
        try:
            data = json.loads(source_code)
            if isinstance(data, dict):
                for i, (k, v) in enumerate(list(data.items())[:10]):
                    if isinstance(v, (str, int, float, bool)):
                        pf.constants.append(ConstantDef(name=k, value=str(v), line=i + 1, var_kind="constant"))
        except (json.JSONDecodeError, AttributeError):
            pass
        return pf


# ── Markdown ──────────────────────────────────────────────────────────────────

class MarkdownParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        pf = _stub(file_path, "markdown")
        for i, line in enumerate(source_code.splitlines(), 1):
            m = re.match(r"^(#{1,3})\s+(.+)", line)
            if m:
                level = len(m.group(1))
                heading = m.group(2).strip()
                pf.constants.append(ConstantDef(
                    name=f"h{level}:{heading}", value=heading, line=i, var_kind="instance",
                ))
        return pf


# ── YAML ──────────────────────────────────────────────────────────────────────

class YamlParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        pf = _stub(file_path, "yaml")
        # Capture top-level keys and their scalar values without a heavy dependency
        for i, line in enumerate(source_code.splitlines(), 1):
            # top-level key: value (no leading spaces)
            m = re.match(r"^([A-Za-z_][\w.\-]*)\s*:\s*(.+)", line)
            if m:
                key, val = m.group(1), m.group(2).strip().strip('"\'')
                if val and not val.startswith("{") and not val.startswith("["):
                    pf.constants.append(ConstantDef(name=key, value=val, line=i, var_kind="constant"))
        return pf


# ── HTML ──────────────────────────────────────────────────────────────────────

class HtmlParser(BaseParser):
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        pf = _stub(file_path, "html")
        # title
        m = re.search(r"<title[^>]*>([^<]+)</title>", source_code, re.IGNORECASE)
        if m:
            pf.constants.append(ConstantDef(name="title", value=m.group(1).strip(), line=1, var_kind="constant"))
        # external scripts
        for i, src in enumerate(re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', source_code, re.IGNORECASE), 1):
            pf.imports.append(ImportDef(source=src, resolved_file=None, bindings=[], is_reexport=False))
        # stylesheets
        for href in re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', source_code, re.IGNORECASE):
            pf.imports.append(ImportDef(source=href, resolved_file=None, bindings=[], is_reexport=False))
        return pf
