#!/usr/bin/env python

import shutil
import hashlib
from pathlib import Path
from amd_ucode_patch.parse import ucode_patch_parse


def file_sha256(file: Path):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with file.open('rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def ucode_patch_name(patch: Path) -> str:
    # Format should be:
    # cpuid<cpuid>_rev<revision>_date<yyyymmdd>.bin
    ucodepatch = ucode_patch_parse(patch)
    return f"family{ucodepatch.header.cpu_family:02x}_cpuid{ucodepatch.header.cpuid_str}_rev{ucodepatch.header.revision:08x}_date{ucodepatch.header.year:04}{ucodepatch.header.month:02}{ucodepatch.header.day:02}.bin"


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
