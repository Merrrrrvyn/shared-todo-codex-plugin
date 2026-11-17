"""Offline tests for the WorkBuddy connector and skill packager."""

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from importlib import import_module
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
workbuddy_packager = import_module("package_workbuddy")


VALID_SKILL = """---
name: shared-todo
description: Use Shared Todo to manage lists and tasks.
---

# Shared Todo

Use the connector tools to manage tasks.
"""


class WorkBuddyFixture:
    def create_source(self, path):
        path.mkdir(parents=True)
        (path / "README.md").write_text(
            "# Shared Todo for WorkBuddy\n\nSetup and usage.\n", encoding="utf-8"
        )
        (path / "connector.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "shared-todo": {
                            "type": "http",
                            "url": "https://todo.example.test/mcp",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        skill_path = path / "skills/shared-todo/SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(VALID_SKILL, encoding="utf-8")
        return path


class ValidateUrlTests(unittest.TestCase):
    def test_accepts_https_and_returns_original_value(self):
        url = "https://todo.example.test/mcp"
        self.assertEqual(workbuddy_packager.validate_url(url), url)

    def test_rejects_credentials_query_fragment_and_whitespace(self):
        invalid_urls = (
            "https://alice:secret@todo.example.test/mcp",
            "https://todo.example.test/mcp?access_token=secret",
            "https://todo.example.test/mcp#token",
            " https://todo.example.test/mcp",
            "https://todo.example.test/mcp ",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                workbuddy_packager.validate_url(url)

    def test_rejects_malformed_and_out_of_range_ports(self):
        for url in (
            "https://todo.example.test:not-a-port/mcp",
            "https://todo.example.test:99999/mcp",
            "https://todo.example.test:-1/mcp",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                workbuddy_packager.validate_url(url)

    def test_local_http_requires_opt_in_and_loopback(self):
        for url in (
            "http://localhost:8080/mcp",
            "http://127.0.0.1:8080/mcp",
            "http://[::1]:8080/mcp",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    workbuddy_packager.validate_url(url)
                self.assertEqual(
                    workbuddy_packager.validate_url(url, allow_local_http=True), url
                )
        for url in (
            "http://todo.example.test/mcp",
            "http://127.0.0.2/mcp",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                workbuddy_packager.validate_url(url, allow_local_http=True)


class PackageValidationTests(WorkBuddyFixture, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.source = self.create_source(self.temp_path / "source")

    def read_connector(self):
        return json.loads((self.source / "connector.json").read_text(encoding="utf-8"))

    def write_connector(self, payload):
        (self.source / "connector.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_accepts_minimal_valid_workbuddy_package(self):
        connector = workbuddy_packager.validate_package(self.source)
        self.assertEqual(
            connector["mcpServers"]["shared-todo"]["url"],
            "https://todo.example.test/mcp",
        )

    def test_rejects_connector_top_level_and_server_extras(self):
        connector = self.read_connector()
        invalid_payloads = (
            {**connector, "metadata": {"token": "secret"}},
            {"mcpServers": {"other": connector["mcpServers"]["shared-todo"]}},
            {
                "mcpServers": {
                    **connector["mcpServers"],
                    "other": {"type": "http", "url": "https://other.test/mcp"},
                }
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.write_connector(payload)
                with self.assertRaises(ValueError):
                    workbuddy_packager.validate_package(self.source)

        server = connector["mcpServers"]["shared-todo"]
        for key, value in (
            ("token", "must-not-be-bundled"),
            ("scopes", ["todo:read"]),
            ("headers", {"Authorization": "secret"}),
            ("command", "node"),
            ("env", {"TOKEN": "secret"}),
        ):
            with self.subTest(key=key):
                self.write_connector(
                    {"mcpServers": {"shared-todo": {**server, key: value}}}
                )
                with self.assertRaisesRegex(ValueError, "只允许 type 和 url"):
                    workbuddy_packager.validate_package(self.source)

    def test_rejects_non_http_or_invalid_url(self):
        connector = self.read_connector()
        for server in (
            {"type": "stdio", "url": "https://todo.example.test/mcp"},
            {"type": "http", "url": "http://todo.example.test/mcp"},
        ):
            with self.subTest(server=server):
                self.write_connector({"mcpServers": {"shared-todo": server}})
                with self.assertRaises(ValueError):
                    workbuddy_packager.validate_package(self.source)
        self.write_connector(connector)

    def test_rejects_skill_without_required_frontmatter(self):
        skill = self.source / workbuddy_packager.SKILL
        original = skill.read_text(encoding="utf-8")
        bad_skills = (
            "# no frontmatter\n",
            "---\nname: other\ndescription: use it\n---\n",
            "---\nname: shared-todo\ndescription: \n---\n",
            "---\nname: shared-todo\ndescription: null\n---\n",
            "---\nname: shared-todo\n---\n",
        )
        for content in bad_skills:
            with self.subTest(content=content):
                skill.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    workbuddy_packager.validate_package(self.source)
        skill.write_text(original, encoding="utf-8")

    def test_rejects_relative_skill_references_outside_allowlist(self):
        skill = self.source / workbuddy_packager.SKILL
        skill.write_text(VALID_SKILL + "\n[Contract](references/contract.md)\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "未纳入固定白名单"):
            workbuddy_packager.validate_package(self.source)

    def test_rejects_symlinked_required_file_and_ancestor(self):
        readme = self.source / "README.md"
        outside = self.temp_path / "outside.md"
        outside.write_text("external", encoding="utf-8")
        readme.unlink()
        readme.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "符号链接"):
            workbuddy_packager.validate_package(self.source)

        readme.unlink()
        readme.write_text("# Readme", encoding="utf-8")
        skill_dir = self.source / "skills"
        shutil.rmtree(skill_dir)
        external_skill = self.temp_path / "outside-skill"
        external_skill.mkdir()
        (external_skill / "shared-todo").mkdir()
        (external_skill / "shared-todo/SKILL.md").write_text(
            VALID_SKILL, encoding="utf-8"
        )
        skill_dir.symlink_to(external_skill, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "符号链接"):
            workbuddy_packager.validate_package(self.source)

    def test_rejects_symlinked_parent_of_source_root(self):
        real_parent = self.temp_path / "real-parent"
        real_source = self.create_source(real_parent / "source")
        alias_parent = self.temp_path / "alias-parent"
        alias_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "源目录不能是符号链接"):
            workbuddy_packager.validate_package(alias_parent / real_source.name)

    def test_rejects_dangling_symlinked_source_file(self):
        skill = self.source / workbuddy_packager.SKILL
        skill.unlink()
        skill.symlink_to(self.temp_path / "missing.md")
        with self.assertRaisesRegex(ValueError, "符号链接"):
            workbuddy_packager.validate_package(self.source)


class BuildPackageTests(WorkBuddyFixture, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.source = self.create_source(self.temp_path / "source")
        self.output = self.temp_path / "dist/workbuddy"

    def test_build_contains_skill_zip_unpacked_skill_and_valid_checksums(self):
        destination, archive = workbuddy_packager.build_package(
            self.source, self.output
        )
        self.assertEqual(destination.name, "shared-todo-workbuddy-1.0.0")
        self.assertEqual(archive.name, "shared-todo-skill.zip")
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(bundle.namelist(), ["shared-todo/SKILL.md"])
            self.assertEqual(
                bundle.read("shared-todo/SKILL.md"),
                (destination / workbuddy_packager.SKILL).read_bytes(),
            )

        checksums = json.loads(
            (destination / "SHA256SUMS.json").read_text(encoding="utf-8")
        )
        self.assertEqual(checksums["algorithm"], "SHA-256")
        self.assertEqual(
            set(checksums["files"]),
            {"README.md", "connector.json", "skills/shared-todo/SKILL.md", "shared-todo-skill.zip"},
        )
        for relative, expected_digest in checksums["files"].items():
            with self.subTest(path=relative):
                self.assertEqual(
                    hashlib.sha256((destination / relative).read_bytes()).hexdigest(),
                    expected_digest,
                )

    def test_url_override_changes_only_packaged_connector(self):
        source_connector = self.source / "connector.json"
        original = source_connector.read_bytes()
        override = "https://staging.example.test/mcp"
        destination, _ = workbuddy_packager.build_package(
            self.source, self.output, mcp_url=override
        )
        self.assertEqual(source_connector.read_bytes(), original)
        packaged = json.loads((destination / "connector.json").read_text(encoding="utf-8"))
        self.assertEqual(packaged["mcpServers"]["shared-todo"]["url"], override)

    def test_allowlist_excludes_sentinel_secrets_and_codex_metadata(self):
        sentinels = (
            self.source / ".env",
            self.source / "access_token.txt",
            self.source / ".codex-plugin/token.json",
            self.source / "credentials.json",
            self.source / "skills/shared-todo/references/private.md",
        )
        for path in sentinels:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("SENTINEL_SECRET_7c21", encoding="utf-8")

        destination, archive = workbuddy_packager.build_package(
            self.source, self.output
        )
        included = {
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            included,
            {
                "README.md",
                "connector.json",
                "skills/shared-todo/SKILL.md",
                "shared-todo-skill.zip",
                "SHA256SUMS.json",
            },
        )
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(bundle.namelist(), ["shared-todo/SKILL.md"])
            self.assertNotIn(b"SENTINEL_SECRET_7c21", bundle.read("shared-todo/SKILL.md"))
        packaged_text = "".join(
            path.read_text(encoding="utf-8")
            for path in destination.rglob("*")
            if path.is_file() and path.suffix != ".zip"
        )
        self.assertNotIn("SENTINEL_SECRET_7c21", packaged_text)

    def test_refuses_preexisting_bundle_directory_without_overwrite(self):
        destination = self.output / "shared-todo-workbuddy-1.0.0"
        destination.mkdir(parents=True)
        archive = destination / "shared-todo-skill.zip"
        archive.write_bytes(b"existing archive sentinel")
        with self.assertRaisesRegex(ValueError, "已存在"):
            workbuddy_packager.build_package(self.source, self.output)
        self.assertEqual(archive.read_bytes(), b"existing archive sentinel")

    def test_preserves_archive_created_by_another_process_during_build(self):
        destination = self.output.resolve() / "shared-todo-workbuddy-1.0.0"
        archive = destination / "shared-todo-skill.zip"
        original_open = Path.open
        competing_bytes = b"created by another builder"

        def create_competing_archive(path, mode="r", *args, **kwargs):
            if path == archive and mode == "xb":
                archive.write_bytes(competing_bytes)
            return original_open(path, mode, *args, **kwargs)

        with (
            mock.patch.object(Path, "open", new=create_competing_archive),
            self.assertRaises(FileExistsError),
        ):
            workbuddy_packager.build_package(self.source, self.output)
        self.assertEqual(archive.read_bytes(), competing_bytes)
        self.assertEqual(
            {path.name for path in destination.iterdir()}, {"shared-todo-skill.zip"}
        )

    def test_failed_zip_creation_cleans_only_this_builds_outputs(self):
        destination = self.output / "shared-todo-workbuddy-1.0.0"
        with (
            mock.patch.object(
                workbuddy_packager.zipfile,
                "ZipFile",
                side_effect=OSError("zip failed"),
            ),
            self.assertRaisesRegex(OSError, "zip failed"),
        ):
            workbuddy_packager.build_package(self.source, self.output)
        self.assertFalse(destination.exists())

    def test_cli_check_and_invalid_override(self):
        old_source = workbuddy_packager.SOURCE
        workbuddy_packager.SOURCE = self.source
        try:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(workbuddy_packager.main(["--check"]), 0)
            self.assertIn("离线校验通过", stdout.getvalue())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = workbuddy_packager.main(
                    ["--check", "--mcp-url", "https://todo.example.test/mcp?token=secret"]
                )
            self.assertEqual(result, 1)
            self.assertIn("打包失败", stderr.getvalue())
            self.assertFalse(self.output.exists())
        finally:
            workbuddy_packager.SOURCE = old_source

    def test_cli_build_supports_version_and_local_http_opt_in(self):
        old_source = workbuddy_packager.SOURCE
        workbuddy_packager.SOURCE = self.source
        local_url = "http://127.0.0.1:8080/mcp"
        connector = json.loads((self.source / "connector.json").read_text())
        connector["mcpServers"]["shared-todo"]["url"] = local_url
        (self.source / "connector.json").write_text(json.dumps(connector))
        try:
            output = self.temp_path / "cli-output"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rejected = workbuddy_packager.main(
                    ["--output", str(output), "--version", "2.3.4"]
                )
            self.assertEqual(rejected, 1)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                accepted = workbuddy_packager.main(
                    [
                        "--output",
                        str(output),
                        "--version",
                        "2.3.4",
                        "--allow-local-http",
                    ]
                )
            self.assertEqual(accepted, 0)
            self.assertTrue(
                (output / "shared-todo-workbuddy-2.3.4/shared-todo-skill.zip").is_file()
            )
        finally:
            workbuddy_packager.SOURCE = old_source


if __name__ == "__main__":
    unittest.main()
