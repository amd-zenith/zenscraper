#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
Linux firmware repository is a source of uCode container files.
'''

import shutil
from pathlib import Path
from zenscraper.sources.abstract_git_source import AbstractGitSource
from git import Commit
from rich.console import Console
from amd_ucode_container.extract import container_extract


class LinuxFirmwareSource(AbstractGitSource):
    @property
    def source_name(self) -> str:
        return "Linux Firmware"
    
    @property
    def repo_url(self) -> str:
        return "https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git"
    
    @property
    def repo_branch(self):
        return "main"

    @property
    def repo_path(self):
        return "amd-ucode"

    def _scrape_commit(self, console: Console, repo_dir: Path, collectdir: Path, commit: Commit):
        # Create a folder if it does not exist...
        ucode_dir = collectdir / commit.hexsha
        ucode_dir.mkdir(parents=True, exist_ok=True)
        # Copy files
        shutil.copytree(str(repo_dir / self.repo_path), str(ucode_dir), dirs_exist_ok=True)

    def _scrape_container(self, container: Path, outdir: Path) -> int:
        # Create a patches dir...
        patchdir = container.parent / f"{container.name}_extracted/"
        patchdir.mkdir(parents=True, exist_ok=True)

        # Extract the container
        container_extract(container, patchdir)

        # Process all patches
        patches = list(patchdir.glob("*.bin"))
        for patch in patches:
            self.process_ucode_patch(patch, outdir)

        # Remove the patches dir...
        if patchdir.exists():
            shutil.rmtree(patchdir)

        return len(patches)

    def _scrape_collection(self, console: Console, collectdir: Path, outdir: Path):
        containers = list(collectdir.glob("**/*.bin"))
        console.log(f"Extracting {len(containers)} uCode containers...")
        patchnum = 0
        for container in containers:
            patchnum += self._scrape_container(container, outdir)
        return patchnum
