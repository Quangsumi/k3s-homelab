"""Exercise real local Git clones and restarts, without Coder or Kubernetes."""

import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


STARTUP = Path(__file__).resolve().parents[1] / "startup.sh"


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repos = self.root / "home" / "repos"
        self.sources = self.root / "sources"
        self.sources.mkdir()
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        editor = bin_dir / "code-server"
        editor.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$EDITOR_ARGS"\n')
        editor.chmod(0o755)
        self.env = dict(os.environ)
        self.env.update(
            PATH=f"{bin_dir}:{os.environ['PATH']}",
            REPO_ROOT=str(self.repos),
            EDITOR_ARGS=str(self.root / "editor-args"),
            GIT_CONFIG_GLOBAL=str(self.root / "gitconfig"),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Test Developer",
            GIT_AUTHOR_EMAIL="test@example.com",
            GIT_COMMITTER_NAME="Test Developer",
            GIT_COMMITTER_EMAIL="test@example.com",
        )
        self.git("config", "--global", f"url.file://{self.sources}/.insteadOf", "https://git.example/")

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.root, env=self.env,
            check=True, text=True, capture_output=True,
        ).stdout.strip()

    def source(self, name):
        path = self.sources / f"{name}.git"
        self.git("init", str(path))
        (path / "README.md").write_text("initial\n")
        self.git("add", ".", cwd=path)
        self.git("commit", "-m", "initial", cwd=path)
        return path

    def start(self, *names):
        env = dict(self.env, REPO_URLS="\n".join(f"https://git.example/{n}.git" for n in names))
        marker = self.root / "editor-args"
        marker.unlink(missing_ok=True)
        result = subprocess.run(
            ["sh", str(STARTUP)], env=env, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        # The startup script launches the editor asynchronously.
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if marker.exists() and str(self.repos) in marker.read_text():
                break
            time.sleep(0.01)
        self.assertTrue(marker.exists(), "The editor must launch even if cloning fails")
        self.assertIn(str(self.repos), marker.read_text())
        return result

    def test_restart_preserves_edits_and_does_not_pull(self):
        source = self.source("frontend")
        self.source("backend")
        self.start("frontend", "backend")
        frontend = self.repos / "frontend"
        old_head = self.git("rev-parse", "HEAD", cwd=frontend)
        (frontend / "README.md").write_text("unsaved-to-git work\n")
        (frontend / "notes.txt").write_text("untracked\n")
        (source / "remote-only.txt").write_text("new upstream commit\n")
        self.git("add", ".", cwd=source)
        self.git("commit", "-m", "upstream", cwd=source)
        self.start("frontend", "backend")
        self.assertEqual(old_head, self.git("rev-parse", "HEAD", cwd=frontend))
        self.assertEqual("unsaved-to-git work\n", (frontend / "README.md").read_text())
        self.assertTrue((frontend / "notes.txt").is_file())
        self.assertFalse((frontend / "remote-only.txt").exists())

    def test_adding_and_removing_urls_keeps_existing_repos(self):
        self.source("frontend")
        self.source("backend")
        self.start("frontend")
        self.start("frontend", "backend")
        self.start("backend")
        self.assertTrue((self.repos / "frontend" / ".git").is_dir())
        self.assertTrue((self.repos / "backend" / ".git").is_dir())

    def test_failed_clone_still_opens_editor_and_can_retry(self):
        result = self.start("missing")
        self.assertIn("Clone failed", result.stderr)
        self.assertFalse((self.repos / "missing").exists())
        self.assertEqual([], list(self.repos.glob(".clone-*")))
        self.source("missing")
        self.start("missing")
        self.assertTrue((self.repos / "missing" / ".git").is_dir())

    def test_empty_workspace_and_manual_paths_are_preserved(self):
        self.start()
        (self.repos / "manual").write_text("existing file")
        (self.repos / "linked").symlink_to("missing-target")
        self.start("manual", "linked")
        self.assertEqual("existing file", (self.repos / "manual").read_text())
        self.assertTrue((self.repos / "linked").is_symlink())


if __name__ == "__main__":
    unittest.main()
