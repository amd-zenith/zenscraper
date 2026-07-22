#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path
from zenscraper.utils.sha256 import file_sha256
from amd_ucode_patch.parse import ucode_patch_parse
from amd_ucode_patch.naming import ucode_patch_name as patch_name


def ucode_patch_name(patch: Path) -> str:
    # Format should be:
    # family<family>_cpuid<cpuid>_rev<revision>_date<yyyymmdd>_enc<ee>_sha<hash12>.bin
    ucodepatch = ucode_patch_parse(patch)
    short_hash = file_sha256(patch)[:12]
    name = patch_name(ucodepatch)
    return name
