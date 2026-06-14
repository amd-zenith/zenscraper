#!/usr/bin/env python
'''
https://github.com/platomav/CPUMicrocodes
'''

import shutil
from pathlib import Path
from zenscraper.sources.abstract_git_source import AbstractGitSource
from git import Commit
from rich.console import Console


class PlatomavCpumicrocodesSource(AbstractGitSource):
    @property
    def source_name(self) -> str:
        return "Platomav CPUMicrocodes"

    @property
    def repo_url(self) -> str:
        return "https://github.com/platomav/CPUMicrocodes.git"

    @property
    def repo_branch(self) -> str:
        return "master"

    @property
    def repo_path(self) -> str:
        return "AMD/"

    def _scrape_commit(self, console: Console, repo_dir: Path, collectdir: Path, commit: Commit):
        # Create a folder for this commit if it does not exist...
        patch_dir = collectdir / commit.hexsha
        patch_dir.mkdir(parents=True, exist_ok=True)
        # Copy patches from this snapshot
        shutil.copytree(str(repo_dir / self.repo_path), str(patch_dir), dirs_exist_ok=True)

    def _scrape_collection(self, console: Console, collectdir: Path, outdir: Path):
        console.log("Obtaining all uCode patches...")
        patches = list(collectdir.glob("**/*.bin"))
        for patch in patches:
            self.process_ucode_patch(patch, outdir)
        return len(patches)
