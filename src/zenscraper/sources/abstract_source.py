#!/usr/bin/env python

import shutil
from pathlib import Path
from abc import ABC, abstractmethod
from zenscraper.utils.patch import ucode_patch_name
from zenscraper.utils.sha256 import file_sha256
from rich.console import Console


class AbstractSource(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def _scrape(self, console: Console, cachedir: Path, tmpdir: Path, outdir: Path):
        '''
        Actual scrape implementation.
        Cache directory is not deleted between runs.
        Tmp directory is cleared between runs.
        '''
        raise NotImplementedError()

    def process_ucode_patch(self, patch: Path, outdir: Path):
        name = ucode_patch_name(patch)
        patchesdir = outdir / "patches"
        patchesdir.mkdir(parents=True, exist_ok=True)
        dst = patchesdir / name
        hash = file_sha256(patch)
        if dst.exists() and file_sha256(dst) != hash:
            raise Exception(f"{name} already exists and has a different hash!")
        else:
            shutil.copy(patch, dst)

    def scrape(self, console: Console, workdir: Path, outdir: Path):
        cachedir = workdir / "cache"
        tmpdir = workdir / "tmp"

        console.log(f"Scraping the {self.source_name} source...")

        patchnum = self._scrape(console, cachedir, tmpdir, outdir)

        console.log(f"Processed {patchnum} uCode patches!")

        if tmpdir.exists():
            shutil.rmtree(tmpdir)

        console.log(f"The {self.source_name} source has been processed!")
