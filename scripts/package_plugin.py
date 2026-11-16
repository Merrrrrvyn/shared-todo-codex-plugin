"""Validate and package the Codex marketplace without credentials or local state."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = Path("plugins/shared-todo")
MANIFEST = PLUGIN / ".codex-plugin/plugin.json"
MCP = PLUGIN / ".mcp.json"
MARKETPLACE = Path(".agents/plugins/marketplace.json")
SKILL = PLUGIN / "skills/shared-todo/SKILL.md"
CONTRACT = PLUGIN / "skills/shared-todo/references/mcp-contract.md"
FILES = (
    MARKETPLACE,
    MANIFEST,
    MCP,
    SKILL,
    CONTRACT,
    Path("README.md"),
)
EXPECTED_TOOLS = {
    "list_templates": "todo:read",
    "list_lists": "todo:read",
    "get_list": "todo:read",
    "create_list": "list:write",
    "update_list": "list:write",
    "delete_list": "list:delete",
    "list_members": "todo:read",
    "list_todos": "todo:read",
    "get_todo": "todo:read",
    "create_todo": "todo:write",
    "update_todo": "todo:write",
    "delete_todo": "todo:delete",
}


def validate_url(value: str, *, allow_local_http: bool = False) -> str:
    """Accept HTTPS endpoints; allow explicit loopback HTTP for development only."""
    if not isinstance(value, str):
        raise TypeError("MCP 地址必须是字符串")
    parsed = urlsplit(value)
    local_http = (
        allow_local_http
        and parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    )
    if not parsed.hostname or (parsed.scheme != "https" and not local_http):
        raise ValueError("MCP 地址必须使用 HTTPS；本机 HTTP 需要 --allow-local-http")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("MCP 地址不能包含账号或密码")
    if parsed.query or parsed.fragment:
        raise ValueError("MCP 地址不能包含查询参数或片段，避免泄漏凭据")
    if any(character.isspace() for character in value):
        raise ValueError("MCP 地址不能包含空白字符")
    # Accessing port also rejects malformed or out-of-range port numbers.
    _ = parsed.port
    return value


def load_json(root: Path, relative: Path) -> dict:
    """Load a required JSON object from the package source."""
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"缺少普通文件：{relative}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON 顶层必须是对象：{relative}")
    return payload


def validate_documented_contract(root: Path) -> None:
    """Keep the shipped tool table and template guidance aligned with the API."""
    contract = (root / CONTRACT).read_text(encoding="utf-8")
    rows = {
        name: line
        for line in contract.splitlines()
        if (match := re.match(r"^\| `([a-z_]+)` \|", line))
        for name in (match.group(1),)
    }
    if set(rows) != set(EXPECTED_TOOLS) or len(rows) != len(EXPECTED_TOOLS):
        raise ValueError("MCP 接口约定必须准确列出全部 12 个工具")
    for tool, scope in EXPECTED_TOOLS.items():
        if scope not in rows[tool]:
            raise ValueError(f"MCP 工具 {tool} 的权限范围文档不正确")
    if "`list_templates` | 无 |" not in rows["list_templates"]:
        raise ValueError("list_templates 必须文档化为无参数工具")
    if "template?: string|null" not in rows["create_list"]:
        raise ValueError("create_list 必须文档化可选模板 ID")


def validate_package(root: Path, *, allow_local_http: bool = False) -> dict:
    """Check the fixed bundle and return its manifest."""
    root = root.resolve()
    for relative in FILES:
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root)
        ):
            raise ValueError(f"缺少或不安全的发布文件：{relative}")
    validate_documented_contract(root)
    manifest = load_json(root, MANIFEST)
    if manifest.get("name") != "shared-todo":
        raise ValueError("插件名称必须为 shared-todo")
    version = manifest.get("version", "")
    if (
        not isinstance(version, str)
        or not version
        or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
            for character in version
        )
    ):
        raise ValueError("版本号缺失或包含不安全字符")
    if (
        manifest.get("skills") != "./skills/"
        or manifest.get("mcpServers") != "./.mcp.json"
    ):
        raise ValueError("插件必须引用打包的 skills 和 MCP 配置")
    marketplace = load_json(root, MARKETPLACE)
    entries = marketplace.get("plugins", [])
    if not isinstance(entries, list):
        raise TypeError("marketplace 的 plugins 必须是数组")
    if marketplace.get("name") != "shared-todo" or len(entries) != 1:
        raise ValueError("marketplace 必须仅包含 shared-todo 插件")
    entry = entries[0]
    if not isinstance(entry, dict):
        raise TypeError("marketplace 插件条目必须是对象")
    if entry.get("name") != "shared-todo" or entry.get("source") != {
        "source": "local",
        "path": "./plugins/shared-todo",
    }:
        raise ValueError("marketplace 插件来源必须是包内目录")
    servers = load_json(root, MCP).get("mcpServers", {})
    if not isinstance(servers, dict):
        raise TypeError("mcpServers 必须是对象")
    if set(servers) != {"shared-todo"}:
        raise ValueError("必须且只能配置 shared-todo MCP")
    server = servers["shared-todo"]
    if not isinstance(server, dict):
        raise TypeError("MCP 服务器配置必须是对象")
    if set(server) != {"type", "url", "scopes"} or server["type"] != "http":
        raise ValueError("MCP 仅允许 HTTP 地址与授权范围，不允许内置凭据")
    validate_url(server["url"], allow_local_http=allow_local_http)
    if server["scopes"] != ["todo:read", "todo:write", "todo:delete", "list:write", "list:delete"]:
        raise ValueError("MCP 授权范围不符合待办接口约定")
    return manifest


def build_package(
    root: Path,
    output: Path,
    *,
    mcp_url: str | None = None,
    allow_local_http: bool = False,
) -> tuple[Path, Path]:
    """Build an allowlisted marketplace directory and its distributable tarball."""
    manifest = validate_package(root, allow_local_http=allow_local_http)
    if mcp_url is not None:
        validate_url(mcp_url, allow_local_http=allow_local_http)
    name = f"shared-todo-codex-{manifest['version']}"
    destination = output.resolve() / name
    archive = output.resolve() / f"{name}.tar.gz"
    if (
        destination.exists()
        or destination.is_symlink()
        or archive.exists()
        or archive.is_symlink()
    ):
        raise ValueError("发布产物已存在，请使用新的 --output 目录，避免覆盖")
    # A failed input check must not create or overwrite any output.
    destination.mkdir(parents=True)
    archive_created = False
    try:
        for relative in FILES:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        if mcp_url is not None:
            config = load_json(destination, MCP)
            config["mcpServers"]["shared-todo"]["url"] = mcp_url
            (destination / MCP).write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        validate_package(destination, allow_local_http=allow_local_http)
        with archive.open("xb") as archive_file:
            archive_created = True
            with tarfile.open(fileobj=archive_file, mode="w:gz") as bundle:
                for relative in FILES:
                    bundle.add(
                        destination / relative, arcname=str(Path(name) / relative)
                    )
    except Exception:
        shutil.rmtree(destination)
        if archive_created:
            archive.unlink(missing_ok=True)
        raise
    return destination, archive


def main(argv: list[str] | None = None) -> int:
    """Run offline validation or create a distributable package."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="仅离线校验，不请求服务端")
    parser.add_argument("--mcp-url", help="覆盖发布产物中的 MCP 地址，不修改源文件")
    parser.add_argument(
        "--allow-local-http", action="store_true", help="允许 loopback HTTP 联调"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args(argv)
    try:
        if args.check:
            validate_package(ROOT, allow_local_http=args.allow_local_http)
            if args.mcp_url is not None:
                validate_url(args.mcp_url, allow_local_http=args.allow_local_http)
            print("插件包离线校验通过；未验证远程 MCP/OAuth 可用性。")
        else:
            destination, archive = build_package(
                ROOT,
                args.output,
                mcp_url=args.mcp_url,
                allow_local_http=args.allow_local_http,
            )
            print(f"Marketplace: {destination}\nArchive: {archive}")
            print("仅完成打包；发布前需完成 MCP/OAuth 服务联调。")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"打包失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
