#!/usr/bin/env python

from pathlib import Path
from zenscraper.utils.sha256 import file_sha256
from amd_ucode_patch.parse import ucode_patch_parse


def ucode_patch_name(patch: Path) -> str:
    # Format should be:
    # family<family>_cpuid<cpuid>_rev<revision>_date<yyyymmdd>_enc<ee>_sha<hash12>.bin
    ucodepatch = ucode_patch_parse(patch)
    short_hash = file_sha256(patch)[:12]
    name = f"family{ucodepatch.header.cpu_family:02x}_cpuid{ucodepatch.header.cpuid_str}_rev{ucodepatch.header.update_revision:08x}_date{ucodepatch.header.year:04}{ucodepatch.header.month:02}{ucodepatch.header.day:02}"
    if ucodepatch.verified_header is not None:
        name += f"_enc{ucodepatch.verified_header.encrypted:02}"
    name += f"_sha{short_hash}"
    name += ".bin"
    return name
