#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
Patches collected by earlier versions of the tool may be stored under names that
no longer match the current naming standard. Normalize them before scraping so
the collection stays consistent and freshly scraped patches do not end up stored
twice under two different names.
'''

import re
from pathlib import Path
from rich.console import Console
from amd_ucode_patch.structures.patch import Patch
from zenscraper.utils.sha256 import file_sha256

# Names this tool has given to collected patches. The current standard always
# carries the _enc part, older ones left it out when the patch had no body
# header. A patch file is only ever renamed when its name matches, so unrelated
# files that happen to sit in the patches directory are left untouched.
COLLECTED_PATCH_NAME = re.compile(
    r"^family[0-9a-f]{2}"
    r"_cpuid[0-9A-Fa-f]{8}"
    r"_rev[0-9a-fA-F]+"
    r"_date[0-9]{8}"
    r"(?:_enc[0-9]{2})?"
    r"_sha[0-9a-f]{12}\.bin$"
)


def _outdated_patches(console: Console, patchesdir: Path) -> list[tuple[Path, str]]:
    '''
    Pair every stored patch that is not named after the current standard with
    the name it should be stored under.
    '''
    outdated = []
    for patch in sorted(patchesdir.glob("*.bin")):
        if not COLLECTED_PATCH_NAME.match(patch.name):
            continue
        try:
            name = Patch.from_file(patch).name_canonical
        except Exception as e:
            console.log(f"Skipping {patch.name}, it cannot be parsed as a uCode patch: {e}")
            continue
        if name != patch.name:
            outdated.append((patch, name))
    return outdated


def normalize_patch_names(console: Console, outdir: Path) -> int:
    '''
    Rename every uCode patch in outdir that does not conform to the current
    naming standard. A patch whose name is already taken by an identical patch
    is a leftover duplicate and gets dropped.
    Return the number of patches that were not conforming.
    '''
    patchesdir = outdir / "patches"
    if not patchesdir.is_dir():
        return 0

    console.log("Checking the names of the stored uCode patches...")
    pending = _outdated_patches(console, patchesdir)

    fixed = 0
    # A patch may be waiting for a name another outdated patch still holds, so
    # keep sweeping for as long as renames keep freeing names up.
    while pending:
        held = {patch for patch, _ in pending}
        deferred = []
        for patch, name in pending:
            dst = patchesdir / name

            # A rename that only changes case targets the very same file on a
            # case insensitive filesystem, so it is a rename and not a clash.
            if dst.exists() and not dst.samefile(patch):
                # Whoever holds the name is outdated too and will move away.
                if dst in held:
                    deferred.append((patch, name))
                    continue
                if file_sha256(dst) != file_sha256(patch):
                    raise Exception(f"{name} already exists and has a different hash!")
                console.log(f"Dropping {patch.name}, {name} already holds the same patch")
                patch.unlink()
                fixed += 1
                continue

            console.log(f"Renaming {patch.name} to {name}")
            patch.replace(dst)
            fixed += 1

        if len(deferred) == len(pending):
            stuck = ", ".join(sorted(patch.name for patch, _ in deferred))
            raise Exception(f"Could not settle the names of these uCode patches: {stuck}")
        pending = deferred

    return fixed
