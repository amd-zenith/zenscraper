# ZenScraper

[![Build](https://github.com/amd-zenith/zenscraper/actions/workflows/build.yml/badge.svg)](https://github.com/amd-zenith/zenscraper/actions/workflows/build.yml)
[![CodeQL](https://github.com/amd-zenith/zenscraper/actions/workflows/codeql.yml/badge.svg)](https://github.com/amd-zenith/zenscraper/actions/workflows/codeql.yml)
[![PyPI version](https://img.shields.io/pypi/v/zenscraper.svg)](https://pypi.org/project/zenscraper/)
[![Python versions](https://img.shields.io/pypi/pyversions/zenscraper.svg)](https://pypi.org/project/zenscraper/)
[![Snyk package health](https://img.shields.io/badge/Snyk-package%20health-4C4A73?logo=snyk&logoColor=white)](https://snyk.io/advisor/python/zenscraper)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/amd-zenith/zenscraper/badge)](https://scorecard.dev/viewer/?uri=github.com/amd-zenith/zenscraper)

A command line tool to collect AMD uCode!

## Overview

ZenScraper gathers AMD CPU microcode (uCode) patches from public upstream
repositories, extracts the individual patches from their containers, and stores
them under a single directory with a consistent, content-addressed naming
scheme. Patches that already exist are de-duplicated by SHA-256, and a hash
mismatch on a same-named patch is reported as an error.

Currently supported sources:

- **Linux Firmware**: the [`linux-firmware`](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git)
  repository (`amd-ucode` containers, extracted into individual patches).
- **Platomav CPUMicrocodes**: the [platomav/CPUMicrocodes](https://github.com/platomav/CPUMicrocodes)
  repository (AMD patches).

Each source is walked across its full git history, so superseded patches are
collected as well as current ones.

## Installation

```bash
pip install zenscraper
```

## Usage

Run the tool to scrape every supported source into the current directory:

```bash
zenscraper
```

Options:

| Option            | Default                 | Description                                                                             |
| ----------------- | ----------------------- | --------------------------------------------------------------------------------------- |
| `--workdir`, `-w` | `./workdir`             | Directory for temporary and cached files (the cloned repos are kept here between runs). |
| `--outdir`, `-o`  | `.` (current directory) | Directory where the collected patches are stored.                                       |


## Output

Collected patches are written to a `patches/` subdirectory of `--outdir`. Each
file is named after its parsed header fields and a short content hash, for
example:

```
family19_cpuid00A20F12_rev0a201210_date20240611_enc00_sha1a2b3c4d5e6f.bin
```

The fields encode the CPU family, CPU ID, update revision, build date,
encryption flag (when present) and the first 12 hex digits of the patch's
SHA-256 hash.

## Provenance catalog

`catalog.json` is both a manifest of the collection and a record of where its
patches were found upstream. Every stored patch gets an entry carrying:

- **Identity**: its canonical file name, full SHA-256 (the name holds only
  12 digits of it) and size, so the catalog can be used to verify the collection.
- **Metadata**: family, CPU ID, patch level, build date, encryption flag
  and whether the patch is signed, decoded once so consumers do not have to
  parse the binaries to index them.
- **Sightings**: every commit of every source whose tree carried the
  patch, with the path it had there. Patches that ship inside a container record
  the container's path and the patch's position among its uCode sections.
- **`first_seen`**: derived from the sightings: the oldest commit of each
  source that carried the patch.

```json
{
  "name": "family19_cpuid00A20F12_rev0a201210_date20240611_enc00_sha1a2b3c4d5e6f.bin",
  "sha256": "1a2b3c4d5e6f...",
  "size": 5568,
  "family": "0x19",
  "cpuid": "00A20F12",
  "patch_level": "0a201210",
  "date": "2024-06-11",
  "encrypted": false,
  "signed": true,
  "stored": true,
  "first_seen": {
    "linux-firmware": {
      "commit": "abc123...",
      "commit_date": "2024-06-20T12:03:44+00:00",
      "path": "amd-ucode/microcode_amd_fam19h.bin",
      "container_index": 42
    }
  },
  "sightings": [ "..." ]
}
```
