#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
Linux firmware repository is a source of uCode container files.
'''

import re
import shutil
from pathlib import Path
from zenscraper.catalog import Catalog, Sighting, intern
from zenscraper.sources.abstract_git_source import AbstractGitSource
from git import Commit
from rich.console import Console
from amd_ucode_container.extract import container_extract

# Names the container extractor gives the sections it writes out, numbered in
# the order they appear in the container.
EXTRACTED_SECTION = re.compile(r"(\d+)")


def _section_order(patch: Path) -> tuple[int, str]:
    '''
    Restore the order the sections were extracted in, which is the order they
    sit in the container. Extracted names are numbered, so they have to be
    read as numbers and not sorted as text, or section 10 lands before 2.
    '''
    number = EXTRACTED_SECTION.search(patch.stem)
    return (int(number.group(1)) if number else 0, patch.name)


class LinuxFirmwareSource(AbstractGitSource):
    @property
    def source_id(self) -> str:
        return "linux-firmware"

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

    def _scrape_commit(self, console: Console, repo_dir: Path, commitdir: Path, commit: Commit):
        # Copy files
        shutil.copytree(str(repo_dir / self.repo_path), str(commitdir), dirs_exist_ok=True)

    def _scrape_container(self, container: Path, outdir: Path, catalog: Catalog, sighting: Sighting) -> int:
        # Create a patches dir...
        patchdir = container.parent / f"{container.name}_extracted/"
        patchdir.mkdir(parents=True, exist_ok=True)

        # Extract the container
        container_extract(container, patchdir)

        # Process all patches. A patch of this source has no path of its own in
        # the repo, only the container it was extracted from, so its position in
        # that container is what pins it down.
        patches = sorted(patchdir.glob("*.bin"), key=_section_order)
        for index, patch in enumerate(patches, start=1):
            self.process_ucode_patch(patch, outdir, catalog, sighting._replace(container_index=index))

        # Remove the patches dir...
        if patchdir.exists():
            shutil.rmtree(patchdir)

        return len(patches)

    def _scrape_collection(self, console: Console, collectdir: Path, outdir: Path, catalog: Catalog):
        containers = list(collectdir.glob("**/*.bin"))
        console.log(f"Extracting {len(containers)} uCode containers...")
        source = intern(self.source_id)
        patchnum = 0
        for container in containers:
            commit, commit_date, repo_path = self._locate(collectdir, container)
            sighting = Sighting(source=source, commit=commit, commit_date=commit_date, path=repo_path)
            patchnum += self._scrape_container(container, outdir, catalog, sighting)
        return patchnum
