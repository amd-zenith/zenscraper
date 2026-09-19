#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
The provenance catalog: a manifest of every stored uCode patch, together with
every place upstream it was seen.

A source walks its whole git history and copies the full tree at every commit
that touched the watched path, so a patch shows up again in every commit from
the one that introduced it onwards. The catalog keeps all of those sightings,
not just the first, so the record answers when a patch entered a repo, when it
left it, and whether it ever came back. A per-source `first_seen` summary is
derived from them, since that is the question most consumers actually ask and
scanning the whole log to answer it is the cost of keeping it.

A run updates the catalog it finds rather than replacing it. Provenance is
observed, not computed: a commit an earlier run saw carrying a patch really did
carry it, whether or not it is still reachable today, and a source that is not
scraped this time keeps everything recorded about it. So sightings accumulate
and are only ever de-duplicated, never dropped. The same goes for patches: an
entry whose file has since left the collection is kept and marked as no longer
stored instead of being forgotten, and an entry whose patch is renamed follows
it to its new name.
'''

import json
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, NamedTuple

from amd_ucode_patch.structures.patch import Patch
from rich.console import Console

from zenscraper.utils.sha256 import file_sha256

# Bumped whenever the emitted document changes shape, so a consumer can tell
# which fields it is allowed to expect.
SCHEMA_VERSION = 1

# The fields decoded from a patch, in the order they are emitted. They sit
# inline on the entry rather than under a key of their own, so this is also the
# list of entry fields that have to be gathered back up when one is read in.
METADATA_KEYS = ("family", "cpuid", "patch_level", "date", "encrypted", "signed")


def intern(value: str) -> str:
    '''
    Collapse a repeated string onto one object. A sighting log names the same
    few dozen commits and few hundred paths over and over, and interning them is
    the difference between the log costing pointers and costing strings.
    '''
    return sys.intern(value)


class Sighting(NamedTuple):
    '''
    One place a patch was seen upstream: a commit of a source, and the path the
    patch had in that commit's tree.

    A tuple rather than a plain dataclass because there is one of these per
    patch per commit that carried it, and because sorting and de-duplicating
    them is how the log is written out.
    '''
    #: The id of the source the patch was seen in.
    source: str
    #: Hex sha of the commit whose tree carried the patch.
    commit: str
    #: Committer date of that commit, ISO 8601.
    commit_date: str
    #: Path of the file in the repo. For a source that ships patches inside
    #: containers this is the container, not the patch.
    path: str
    #: 1-based position of the patch among the container's uCode sections, or
    #: None when the repo stores the patch as its own file.
    container_index: int | None = None


def _sighting_order(sighting: Sighting) -> tuple:
    '''
    Sort key giving the sighting log a stable order. container_index is folded
    to an int so a source that stores loose patches and one that stores
    containers can sort side by side.
    '''
    return (
        sighting.source,
        sighting.commit_date,
        sighting.commit,
        sighting.path,
        -1 if sighting.container_index is None else sighting.container_index,
    )


@dataclass
class PatchEntry:
    '''A patch the collection knows about: what it is, and everywhere it was seen.'''
    #: Canonical file name the patch is stored under.
    name: str
    #: SHA-256 of the patch, in full. The name carries only 12 digits.
    sha256: str
    #: Size of the patch in bytes.
    size: int
    #: Fields decoded from the patch, so a consumer indexing the collection does
    #: not have to parse the binaries. All None for a stored file that could not
    #: be parsed as a patch.
    metadata: dict[str, Any]
    #: Every sighting of this patch, across every source and every run.
    sightings: list[Sighting] = field(default_factory=list)
    #: Whether the patch is in the collection as of this run. An entry read back
    #: from an earlier catalog whose file has since gone is kept, not dropped,
    #: so what was recorded about it survives.
    stored: bool = False


def _patch_metadata(patch: Patch) -> dict[str, Any]:
    '''Decode the header fields worth carrying in the catalog.'''
    body_header = patch.body.body_header
    return {
        "family": f"0x{patch.header.patch_level.family:02x}",
        "cpuid": f"{patch.header.data.cpuid.cpuid_signature:08X}",
        "patch_level": str(patch.header.patch_level),
        "date": str(patch.header.date),
        "encrypted": bool(body_header.encrypted) if body_header is not None else False,
        "signed": patch.header.signature is not None,
    }


def _unparsed_metadata() -> dict[str, Any]:
    '''
    The metadata of a stored file that could not be parsed as a patch. The keys
    are still there so every entry in the catalog has the same shape.
    '''
    return {key: None for key in METADATA_KEYS}


def _generator_version() -> str:
    try:
        return version("zenscraper")
    except PackageNotFoundError:
        # Running from a source tree that was never installed.
        return "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_block(value: Any, indent: int) -> str:
    '''
    Render a value as pretty-printed JSON sitting `indent` spaces deep. The
    document is written a patch at a time rather than dumped in one go, so that
    a sighting log of any size only ever costs one entry of memory to serialize.
    '''
    return textwrap.indent(json.dumps(value, indent=2), " " * indent)


class Catalog:
    '''The provenance catalog: what earlier runs recorded, plus this one.'''

    def __init__(self):
        self._sources: dict[str, dict[str, Any]] = {}
        self._patches: dict[str, PatchEntry] = {}
        # Entries read back from an earlier catalog carry that catalog's idea of
        # what the patch is. The first time this run collects one, it is decoded
        # afresh, so a fix to how patches are read reaches the stored record.
        self._stale: set[str] = set()

    @classmethod
    def load(cls, path: Path) -> "Catalog":
        '''
        Pick up the catalog an earlier run left behind, so this run adds to it
        instead of starting over. A run with nothing to pick up starts empty.

        A catalog that cannot be read is an error rather than something to work
        around: carrying on would overwrite it, and what it holds cannot be
        rebuilt from repositories whose commits may since have gone.
        '''
        catalog = cls()
        if not path.is_file():
            return catalog
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            raise Exception(f"{path} exists but cannot be read as a catalog: {e}") from e

        found = document.get("schema_version")
        if found != SCHEMA_VERSION:
            raise Exception(
                f"{path} is a schema {found} catalog and this zenscraper writes "
                f"schema {SCHEMA_VERSION}; it was left by a different version of the tool"
            )

        catalog._sources = document.get("sources", {})
        for entry in document.get("patches", []):
            name = entry["name"]
            catalog._patches[name] = PatchEntry(
                name=name,
                sha256=entry["sha256"],
                size=entry["size"],
                metadata={key: entry.get(key) for key in METADATA_KEYS},
                sightings=[
                    Sighting(
                        source=intern(sighting["source"]),
                        commit=intern(sighting["commit"]),
                        commit_date=intern(sighting["commit_date"]),
                        path=intern(sighting["path"]),
                        container_index=sighting["container_index"],
                    )
                    for sighting in entry.get("sightings", [])
                ],
            )
            catalog._stale.add(name)
        return catalog

    def record_source(self, source_id: str, **details: Any):
        '''Record what a source is and what of it was walked this run.'''
        self._sources[source_id] = {**details, "scraped": _now()}

    def record_patch(self, name: str, patch: Patch, size: int, sighting: Sighting):
        '''
        Record a patch that was just collected, and the place it came from.
        The same patch arrives once per commit that carried it, so its identity
        and metadata are only decoded the first time this run sees it.
        '''
        entry = self._patches.get(name)
        if entry is None:
            entry = PatchEntry(name=name, sha256=patch.sha256, size=size, metadata={})
            self._patches[name] = entry
            self._stale.add(name)
        if name in self._stale:
            entry.sha256 = patch.sha256
            entry.size = size
            entry.metadata = _patch_metadata(patch)
            self._stale.discard(name)
        entry.sightings.append(sighting)

    def rename_patch(self, old_name: str, new_name: str):
        '''
        Follow a stored patch that has been renamed, so what was recorded about
        it stays attached to it. When the new name is already taken the two are
        the same patch under two names, and their sightings are pooled.
        '''
        entry = self._patches.pop(old_name, None)
        if entry is None:
            return
        self._stale.discard(old_name)
        held = self._patches.get(new_name)
        if held is not None:
            held.sightings.extend(entry.sightings)
            return
        entry.name = new_name
        self._patches[new_name] = entry
        self._stale.add(new_name)

    def sweep(self, console: Console, patchesdir: Path):
        '''
        Reconcile the catalog with the collection on disk: take in every stored
        patch no source claimed this run, and mark which of the patches on
        record are still there. An entry whose file has gone is kept, since the
        sightings behind it were true when they were made.
        '''
        stored = {path.name for path in patchesdir.glob("*.bin")} if patchesdir.is_dir() else set()

        for name in sorted(stored - set(self._patches)):
            path = patchesdir / name
            try:
                metadata = _patch_metadata(Patch.from_file(path))
            except Exception as e:
                console.log(f"Cataloguing {name} without metadata, it cannot be parsed as a uCode patch: {e}")
                metadata = _unparsed_metadata()
            self._patches[name] = PatchEntry(
                name=name,
                sha256=file_sha256(path),
                size=path.stat().st_size,
                metadata=metadata,
            )

        for name, entry in self._patches.items():
            entry.stored = name in stored

    @property
    def patch_count(self) -> int:
        return len(self._patches)

    @property
    def stored_count(self) -> int:
        return sum(1 for entry in self._patches.values() if entry.stored)

    @property
    def sighting_count(self) -> int:
        return sum(len(set(entry.sightings)) for entry in self._patches.values())

    def _entry_document(self, entry: PatchEntry) -> dict[str, Any]:
        '''Render one patch, sightings and all, as the document describes it.'''
        # A patch can be reached twice within a single commit, and a commit
        # walked again by a later run is seen again, so the log is
        # de-duplicated as it is ordered.
        sightings = sorted(set(entry.sightings), key=_sighting_order)

        # first_seen is derived from the log: the oldest commit of each source
        # that carried the patch, which is the commit that introduced it there.
        first_seen: dict[str, Any] = {}
        for sighting in sightings:
            first_seen.setdefault(sighting.source, {
                "commit": sighting.commit,
                "commit_date": sighting.commit_date,
                "path": sighting.path,
                "container_index": sighting.container_index,
            })

        return {
            "name": entry.name,
            "sha256": entry.sha256,
            "size": entry.size,
            **{key: entry.metadata.get(key) for key in METADATA_KEYS},
            "stored": entry.stored,
            "first_seen": first_seen,
            "sightings": [sighting._asdict() for sighting in sightings],
        }

    def save(self, path: Path):
        '''
        Write the catalog out. The document is fully ordered, so two runs that
        collect the same thing produce the same bytes and a run that collects
        something new shows up as a diff.
        '''
        head = {
            "schema_version": SCHEMA_VERSION,
            "generator": {"name": "zenscraper", "version": _generator_version()},
            "generated": _now(),
            "sources": dict(sorted(self._sources.items())),
            "patch_count": self.patch_count,
            "stored_count": self.stored_count,
            "sighting_count": self.sighting_count,
        }
        entries = [self._patches[name] for name in sorted(self._patches)]

        # Written to a temporary file first so an interrupted run leaves the
        # catalog of the previous one intact rather than a truncated document.
        # There is no rebuilding what a truncated one would have lost.
        tmp = path.with_name(path.name + ".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write("{\n")
            for key, value in head.items():
                f.write(f"  {json.dumps(key)}: {_json_block(value, 2).lstrip()},\n")
            f.write('  "patches": [\n')
            for index, entry in enumerate(entries):
                f.write(_json_block(self._entry_document(entry), 4))
                f.write(",\n" if index < len(entries) - 1 else "\n")
            f.write("  ]\n")
            f.write("}\n")
        tmp.replace(path)
