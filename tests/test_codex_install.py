"""Optional local Codex CLI installation smoke test; never logs in or calls MCP."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
package_plugin = import_module("package_plugin")


CODEX = shutil.which("codex")


@unittest.skipUnless(CODEX, "Codex CLI is not installed")
class CodexInstallSmokeTests(unittest.TestCase):
    def test_marketplace_install_and_mcp_registration_in_isolated_home(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            package_root, _archive = package_plugin.build_package(
                package_plugin.ROOT, temporary_root / "dist"
            )
            codex_home = temporary_root / "codex-home"
            codex_home.mkdir()
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)

            def run_json(*arguments):
                result = subprocess.run(
                    [CODEX, *arguments, "--json"],
                    cwd=package_root,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg="codex {} failed:\n{}".format(
                        " ".join(arguments), result.stderr
                    ),
                )
                return json.loads(result.stdout)

            marketplace = run_json("plugin", "marketplace", "add", str(package_root))
            self.assertEqual(marketplace["marketplaceName"], "shared-todo")

            installed = run_json("plugin", "add", "shared-todo@shared-todo")
            manifest = package_plugin.load_json(package_root, package_plugin.MANIFEST)
            self.assertEqual(installed["pluginId"], "shared-todo@shared-todo")
            self.assertEqual(installed["version"], manifest["version"])

            plugins = run_json("plugin", "list")["installed"]
            plugin = next(
                item
                for item in plugins
                if item["pluginId"] == "shared-todo@shared-todo"
            )
            self.assertTrue(plugin["enabled"])
            self.assertEqual(plugin["version"], manifest["version"])

            servers = run_json("mcp", "list")
            server = next(item for item in servers if item["name"] == "shared-todo")
            self.assertTrue(server["enabled"])
            self.assertEqual(server["transport"]["type"], "streamable_http")
            expected_config = package_plugin.load_json(
                package_root, package_plugin.MCP
            )["mcpServers"]["shared-todo"]
            self.assertEqual(server["transport"]["url"], expected_config["url"])
            self.assertIsNone(server["transport"].get("bearer_token_env_var"))


if __name__ == "__main__":
    unittest.main()
