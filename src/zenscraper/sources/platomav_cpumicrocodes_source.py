#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
https://github.com/platomav/CPUMicrocodes
'''

import shutil
from pathlib import Path
from zenscraper.catalog import Catalog, Sighting, intern
from zenscraper.sources.abstract_git_source import AbstractGitSource
from git import Commit
from rich.console import Console


class PlatomavCpumicrocodesSource(AbstractGitSource):
    @property
    def source_id(self) -> str:
        return "platomav-cpumicrocodes"

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

    def _scrape_commit(self, console: Console, repo_dir: Path, commitdir: Path, commit: Commit):
        # Copy patches from this snapshot
        shutil.copytree(str(repo_dir / self.repo_path), str(commitdir), dirs_exist_ok=True)

    def _scrape_collection(self, console: Console, collectdir: Path, outdir: Path, catalog: Catalog):
        console.log("Obtaining all uCode patches...")
        patches = list(collectdir.glob("**/*.bin"))
        source = intern(self.source_id)
        for patch in patches:
            # This source stores every patch as its own file, so the path it was
            # collected from is the path it has in the repo.
            commit, commit_date, repo_path = self._locate(collectdir, patch)
            self.process_ucode_patch(patch, outdir, catalog, Sighting(
                source=source, commit=commit, commit_date=commit_date, path=repo_path))
        return len(patches)
