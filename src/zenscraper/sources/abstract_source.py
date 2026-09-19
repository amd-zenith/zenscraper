#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later

import shutil
from pathlib import Path
from abc import ABC, abstractmethod
from zenscraper.catalog import Catalog, Sighting
from zenscraper.utils.sha256 import file_sha256
from rich.console import Console
from amd_ucode_patch.structures.patch import Patch


class AbstractSource(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str:
        '''
        Stable slug naming this source in the provenance catalog. Unlike
        source_name it is part of the catalog's contract with its consumers, so
        it outlives any rewording of the display name.
        '''
        raise NotImplementedError()

    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def _scrape(self, console: Console, cachedir: Path, tmpdir: Path, outdir: Path, catalog: Catalog):
        '''
        Actual scrape implementation.
        Cache directory is not deleted between runs.
        Tmp directory is cleared between runs.
        '''
        raise NotImplementedError()

    def process_ucode_patch(self, path: Path, outdir: Path, catalog: Catalog, sighting: Sighting):
        patch = Patch.from_file(path)
        name = patch.name_canonical
        patchesdir = outdir / "patches"
        patchesdir.mkdir(parents=True, exist_ok=True)
        dst = patchesdir / name
        hash = patch.sha256
        if dst.exists() and file_sha256(dst) != hash:
            raise Exception(f"{name} already exists and has a different hash!")
        else:
            shutil.copy(path, dst)
        catalog.record_patch(name, patch, path.stat().st_size, sighting)

    def scrape(self, console: Console, workdir: Path, outdir: Path, catalog: Catalog):
        cachedir = workdir / "cache"
        tmpdir = workdir / "tmp"

        console.log(f"Scraping the {self.source_name} source...")

        patchnum = self._scrape(console, cachedir, tmpdir, outdir, catalog)

        console.log(f"Processed {patchnum} uCode patches!")

        if tmpdir.exists():
            shutil.rmtree(tmpdir)

        console.log(f"The {self.source_name} source has been processed!")
