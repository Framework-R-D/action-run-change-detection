"""Verify sparse checkout and immutable input boundaries without remote operations."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ACTION = Path(__file__).parents[1] / "action.yaml"


class CheckoutContainmentTests(unittest.TestCase):
    """Use ephemeral Git data and sentinel-only action environments."""

    def test_sparse_exclusion_keeps_objects_without_source_files(self) -> None:
        """The pinned checkout pattern must actually exclude tracked files."""
        self.assertIn('sparse-checkout: "!/*"', ACTION.read_text())
        with tempfile.TemporaryDirectory(prefix="sparse-test-") as tmp:
            root = Path(tmp)
            env = {
                "PATH": os.environ["PATH"],
                "HOME": tmp,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "Test",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, env=env, check=True, capture_output=True
                )

            git("init", "--quiet", "--template=")
            (root / "source.sh").write_text("not executed\n")
            git("add", "source.sh")
            git("commit", "--quiet", "-m", "fixture")
            git("sparse-checkout", "set", "--no-cone", "!/*")
            self.assertFalse((root / "source.sh").exists())
            self.assertIn(b"source.sh", git("ls-tree", "--name-only", "HEAD").stdout)

    def test_target_preflight_rejects_output_and_path_injection(self) -> None:
        """Only one valid immutable snapshot can reach checkout."""
        scripts = re.findall(r"^      run: \|\n((?:        .*\n|\n)+)", ACTION.read_text(), re.M)
        script = textwrap.dedent(scripts[0])
        for overrides in [
            {},
            {"INPUT_SHA": "feature"},
            {"INPUT_REPO": "X/y\nsha=evil"},
            {"INPUT_HEAD": "b" * 40},
            {"INPUT_PATH": "../outside"},
        ]:
            with (
                self.subTest(overrides=overrides),
                tempfile.TemporaryDirectory(prefix="preflight-test-") as tmp,
            ):
                output = Path(tmp) / "outputs"
                env = {
                    "PATH": os.environ["PATH"],
                    "HOME": tmp,
                    "GITHUB_WORKSPACE": tmp,
                    "GITHUB_OUTPUT": str(output),
                    "INPUT_SHA": "a" * 40,
                    "INPUT_HEAD": "",
                    "INPUT_REPO": "Example/target",
                    "INPUT_PATH": "source",
                    **overrides,
                }
                result = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True)
                if overrides:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_text(), f"sha={'a' * 40}\n")


if __name__ == "__main__":
    unittest.main()
