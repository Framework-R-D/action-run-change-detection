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
            {"INPUT_PATH": " link/child"},
            {"INPUT_PATH": "link/child "},
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
                if overrides.get("INPUT_PATH") == " link/child":
                    (Path(tmp) / "link").symlink_to(Path(tmp).parent, target_is_directory=True)
                result = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True)
                if overrides:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_text(), f"sha={'a' * 40}\n")

    def test_git_version_check_requires_2_28(self) -> None:
        """Reject versions that trigger the pinned checkout's archive fallback."""
        script = textwrap.dedent(
            re.findall(r"^      run: \|\n((?:        .*\n|\n)+)", ACTION.read_text(), re.M)[0]
        )
        for version, succeeds in [("2.27.9", False), ("2.28.0", True)]:
            with (
                self.subTest(version=version),
                tempfile.TemporaryDirectory(prefix="git-version-test-") as tmp,
            ):
                root = Path(tmp)
                fake_git = root / "git"
                fake_git.write_text(
                    "#!/bin/sh\nprintf 'git version %s\\n' \"$FAKE_GIT_VERSION\"\n"
                )
                fake_git.chmod(0o755)
                output = root / "outputs"
                environment = {
                    "PATH": f"{tmp}:{os.environ['PATH']}",
                    "HOME": tmp,
                    "GITHUB_WORKSPACE": tmp,
                    "GITHUB_OUTPUT": str(output),
                    "INPUT_SHA": "a" * 40,
                    "INPUT_HEAD": "",
                    "INPUT_REPO": "Example/target",
                    "INPUT_PATH": "source",
                    "FAKE_GIT_VERSION": version,
                }
                result = subprocess.run(
                    ["bash", "-e", "-c", script],
                    env=environment,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)
                if succeeds:
                    self.assertEqual(output.read_text(), f"sha={'a' * 40}\n")
                else:
                    self.assertIn("Git 2.28 or newer", result.stderr)
                    self.assertFalse(output.exists())

    def test_branch_base_resolves_to_remote_tracking_commit(self) -> None:
        """Detached SHA checkout still resolves branch-form bases safely."""
        content = ACTION.read_text()
        section = content.split("    - name: Resolve base comparison ref\n", 1)[1]
        script_match = re.search(r"      run: \|\n((?:        .*\n|\n)+)", section, re.M)
        self.assertIsNotNone(script_match)
        script = textwrap.dedent(script_match.group(1))
        with tempfile.TemporaryDirectory(prefix="base-ref-test-") as tmp:
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

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", *args], cwd=root, env=env, check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init", "--quiet", "--template=")
            (root / "tracked.txt").write_text("base\n")
            git("add", "tracked.txt")
            git("commit", "--quiet", "-m", "base")
            base_sha = git("rev-parse", "HEAD")
            git("update-ref", "refs/remotes/origin/main", base_sha)
            git("checkout", "--quiet", "--detach")
            output = root / "outputs"
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                cwd=root,
                env=env | {"INPUT_BASE_REF": "main", "GITHUB_OUTPUT": str(output)},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), f"base-ref={base_sha}\n")

            output.unlink()
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                cwd=root,
                env=env | {"INPUT_BASE_REF": "missing", "GITHUB_OUTPUT": str(output)},
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
