#!/usr/bin/env python

import shutil
from pathlib import Path
from zenscraper.utils.sha256 import file_sha256
from zenscraper.utils.patch import ucode_patch_name


def ucode_patch_process(patch: Path, outdir: Path):
    name = ucode_patch_name(patch)
    patchesdir = outdir / "patches"
    patchesdir.mkdir(parents=True, exist_ok=True)
    dst = patchesdir / name
    hash = file_sha256(patch)
    if dst.exists() and file_sha256(dst) != hash:
        raise Exception(f"{name} already exists and has a different hash!")
    else:
        shutil.copy(patch, dst)
