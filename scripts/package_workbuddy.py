"""Validate and package the WorkBuddy connector and Shared Todo skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from package_plugin import validate_url

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "integrations/workbuddy"
README = Path("README.md")
CONNECTOR = Path("connector.json")
SKILL = Path("skills/shared-todo/SKILL.md")
FILES = (README, CONNECTOR, SKILL)
VERSION = "1.0.0"
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")


def _source_file(root: Path, relative: Path) -> Path:
    """Return a regular allowlisted source file, rejecting symlinked parents."""
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("WorkBuddy 源目录不能是符号链接")
    resolved_root = root.resolve()
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"源文件路径不能包含符号链接：{relative}")
        if not current.exists():
            raise ValueError(f"缺少 WorkBuddy 发布文件：{relative}")
        if index < len(relative.parts) - 1:
            if not current.is_dir():
                raise ValueError(f"源文件父路径不是目录：{relative}")
        elif not current.is_file():
            raise ValueError(f"源文件不是普通文件：{relative}")
    resolved_file = current.resolve()
    if not resolved_file.is_relative_to(resolved_root):
        raise ValueError(f"源文件路径逃逸出 WorkBuddy 目录：{relative}")
    return current


def _relative_skill_references(content: str) -> set[str]:
    """Find local Markdown links that would need to ship with the skill."""
    references: set[str] = set()
    pattern = re.compile(r"!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
    for match in pattern.finditer(content):
        target = match.group(1) or match.group(2)
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        references.add(parsed.path)
    return references


def _validate_skill_frontmatter(content: str) -> None:
    """Require the WorkBuddy skill's name and description in its frontmatter."""
    if not content.startswith("---\n"):
        raise ValueError("Skill 必须以 YAML frontmatter 开头")
    end = content.find("\n---\n", 4)
    if end < 0:
        raise ValueError("Skill frontmatter 缺少结束标记")
    lines = content[4:end].splitlines()
    values: dict[str, tuple[str, int]] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if match:
            values[match.group(1)] = (match.group(2).strip(), index)
    if "name" not in values:
        raise ValueError("Skill frontmatter 缺少 name")
    name = values["name"][0].strip("\"'")
    if name != "shared-todo":
        raise ValueError("Skill frontmatter name 必须为 shared-todo")
    if "description" not in values:
        raise ValueError("Skill frontmatter 缺少 description")
    description, description_index = values["description"]
    if description in {"|", ">", "|-", ">-", "|+", ">+"}:
        description = " ".join(
            line.strip()
            for line in lines[description_index + 1 :]
            if line.startswith((" ", "\t")) and line.strip()
        )
    description = description.strip("\"'").strip()
    if not description or description.lower() in {"null", "~"}:
        raise ValueError("Skill frontmatter description 不能为空")


def validate_package(root: Path, *, allow_local_http: bool = False) -> dict:
    """Validate the fixed WorkBuddy source allowlist and return its connector."""
    for relative in FILES:
        _source_file(root, relative)

    readme = _source_file(root, README).read_text(encoding="utf-8")
    if not readme.strip():
        raise ValueError("WorkBuddy README 不能为空")

    skill_text = _source_file(root, SKILL).read_text(encoding="utf-8")
    _validate_skill_frontmatter(skill_text)
    references = _relative_skill_references(skill_text)
    if references:
        joined = ", ".join(sorted(references))
        raise ValueError(f"Skill 含有未纳入固定白名单的相对引用：{joined}")

    connector_path = _source_file(root, CONNECTOR)
    connector = json.loads(connector_path.read_text(encoding="utf-8"))
    if not isinstance(connector, dict):
        raise TypeError("connector.json 顶层必须是对象")
    if set(connector) != {"mcpServers"}:
        raise ValueError("connector.json 顶层只能包含 mcpServers")
    servers = connector["mcpServers"]
    if not isinstance(servers, dict):
        raise TypeError("mcpServers 必须是对象")
    if set(servers) != {"shared-todo"}:
        raise ValueError("必须且只能配置 shared-todo MCP")
    server = servers["shared-todo"]
    if not isinstance(server, dict):
        raise TypeError("shared-todo MCP 配置必须是对象")
    if set(server) != {"type", "url"}:
        raise ValueError("MCP 只允许 type 和 url，不得携带凭据或其他配置")
    if server["type"] != "http":
        raise ValueError("shared-todo MCP type 必须为 http")
    validate_url(server["url"], allow_local_http=allow_local_http)
    return connector


def _validate_version(version: str) -> str:
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise ValueError("版本号缺失或包含不安全字符")
    return version


def _copy_exclusive(source: Path, target: Path, owned_files: list[Path]) -> None:
    """Copy a validated file without replacing a path created by another process."""
    with source.open("rb") as source_file, target.open("xb") as target_file:
        owned_files.append(target)
        shutil.copyfileobj(source_file, target_file)


def _cleanup_owned_paths(owned_files: list[Path], owned_directories: list[Path]) -> None:
    """Remove only paths created by this build; preserve racing external files."""
    for path in reversed(owned_files):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # The path may have been replaced concurrently; leave it untouched.
            pass
    for path in reversed(owned_directories):
        try:
            path.rmdir()
        except OSError:
            # A concurrent file may be present; do not remove someone else's work.
            pass


def build_package(
    root: Path,
    output: Path,
    *,
    mcp_url: str | None = None,
    allow_local_http: bool = False,
    version: str = VERSION,
) -> tuple[Path, Path]:
    """Create a WorkBuddy bundle using only the fixed source allowlist."""
    _validate_version(version)
    connector = validate_package(root, allow_local_http=allow_local_http)
    if mcp_url is not None:
        validate_url(mcp_url, allow_local_http=allow_local_http)
        connector["mcpServers"]["shared-todo"]["url"] = mcp_url

    output.mkdir(parents=True, exist_ok=True)
    output_root = output.resolve()
    name = f"shared-todo-workbuddy-{version}"
    destination = output_root / name
    if destination.exists() or destination.is_symlink():
        raise ValueError("发布目录已存在，请使用新的 --output 目录，避免覆盖")

    destination.mkdir()
    owned_directories = [destination]
    owned_files: list[Path] = []
    archive = destination / "shared-todo-skill.zip"
    try:
        for relative in (README, SKILL):
            target = destination / relative
            missing_directories = [
                parent
                for parent in target.parents
                if parent != destination and not parent.exists()
            ]
            for parent in reversed(missing_directories):
                parent.mkdir()
                owned_directories.append(parent)
            _copy_exclusive(_source_file(root, relative), target, owned_files)

        connector_copy = destination / CONNECTOR
        with connector_copy.open("x", encoding="utf-8") as connector_file:
            owned_files.append(connector_copy)
            connector_file.write(
                json.dumps(connector, ensure_ascii=False, indent=2) + "\n"
            )

        skill_bytes = (destination / SKILL).read_bytes()
        with archive.open("xb") as archive_file:
            owned_files.append(archive)
            with zipfile.ZipFile(
                archive_file, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as bundle:
                bundle.writestr("shared-todo/SKILL.md", skill_bytes)

        checksum_targets = (README, CONNECTOR, SKILL, Path("shared-todo-skill.zip"))
        checksums = {
            str(relative): hashlib.sha256((destination / relative).read_bytes()).hexdigest()
            for relative in checksum_targets
        }
        checksums_path = destination / "SHA256SUMS.json"
        with checksums_path.open("x", encoding="utf-8") as checksums_file:
            owned_files.append(checksums_path)
            checksums_file.write(
                json.dumps(
                    {"algorithm": "SHA-256", "files": checksums},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
    except Exception:
        _cleanup_owned_paths(owned_files, owned_directories)
        raise
    return destination, archive


def main(argv: list[str] | None = None) -> int:
    """Run offline validation or create the WorkBuddy bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="仅校验，不生成发布文件")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/workbuddy")
    parser.add_argument("--version", default=VERSION, help="独立 WorkBuddy 包版本")
    parser.add_argument("--mcp-url", help="覆盖产物中的 MCP 地址，不修改源文件")
    parser.add_argument(
        "--allow-local-http", action="store_true", help="允许 loopback HTTP 联调"
    )
    args = parser.parse_args(argv)
    try:
        _validate_version(args.version)
        validate_package(SOURCE, allow_local_http=args.allow_local_http)
        if args.mcp_url is not None:
            validate_url(args.mcp_url, allow_local_http=args.allow_local_http)
        if args.check:
            print("WorkBuddy 包离线校验通过；未验证远程 MCP/OAuth 可用性。")
        else:
            destination, archive = build_package(
                SOURCE,
                args.output,
                mcp_url=args.mcp_url,
                allow_local_http=args.allow_local_http,
                version=args.version,
            )
            print(f"Bundle: {destination}\nSkill ZIP: {archive}")
            print("仅完成打包；发布或安装前需完成 WorkBuddy MCP/OAuth 联调。")
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"打包失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
