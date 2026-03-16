import json
import re
from pathlib import Path
from .base import ConfigValue


def parse_tsconfig(file_path: str, content: str) -> list[ConfigValue]:
    values = []
    try:
        data = json.loads(content)
        opts = data.get("compilerOptions", {})
        if "baseUrl" in opts:
            values.append(ConfigValue(key="compilerOptions.baseUrl", value=opts["baseUrl"], source_file=file_path))
        for k, v in opts.get("paths", {}).items():
            values.append(ConfigValue(key=f"compilerOptions.paths.{k}", value=str(v), source_file=file_path))
    except (json.JSONDecodeError, AttributeError):
        pass
    return values


def parse_go_mod(file_path: str, content: str) -> list[ConfigValue]:
    values = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("module "):
            values.append(ConfigValue(key="module", value=line[7:].strip(), source_file=file_path))
            break
    return values


def parse_cargo_toml(file_path: str, content: str) -> list[ConfigValue]:
    values = []
    in_package = False
    for line in content.splitlines():
        line = line.strip()
        if line == "[package]":
            in_package = True
            continue
        if line.startswith("[") and line != "[package]":
            in_package = False
        if in_package:
            if line.startswith("name"):
                v = line.split("=", 1)[1].strip().strip('"')
                values.append(ConfigValue(key="package.name", value=v, source_file=file_path))
            elif line.startswith("version"):
                v = line.split("=", 1)[1].strip().strip('"')
                values.append(ConfigValue(key="package.version", value=v, source_file=file_path))
    return values


def parse_build_gradle(file_path: str, content: str) -> list[ConfigValue]:
    values = []
    for pattern, key in [
        (r"^group\s*=\s*['\"](.+)['\"]", "group"),
        (r"^version\s*=\s*['\"](.+)['\"]", "version"),
    ]:
        m = re.search(pattern, content, re.MULTILINE)
        if m:
            values.append(ConfigValue(key=key, value=m.group(1), source_file=file_path))
    return values


def parse_gemfile(file_path: str, content: str) -> list[ConfigValue]:
    values = []
    for line in content.splitlines():
        m = re.match(r"^\s*gem\s+['\"]([^'\"]+)['\"]", line)
        if m:
            values.append(ConfigValue(key="gem", value=m.group(1), source_file=file_path))
    return values


CONFIG_PARSERS = {
    "tsconfig.json": parse_tsconfig,
    "go.mod": parse_go_mod,
    "Cargo.toml": parse_cargo_toml,
    "build.gradle": parse_build_gradle,
    "Gemfile": parse_gemfile,
}


def parse_config_file(file_path: str, content: str) -> list[ConfigValue]:
    name = Path(file_path).name
    parser_fn = CONFIG_PARSERS.get(name)
    if parser_fn:
        return parser_fn(file_path, content)
    return []
