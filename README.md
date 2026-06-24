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

- **Linux Firmware** &mdash; the [`linux-firmware`](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git)
  repository (`amd-ucode` containers, extracted into individual patches).
- **Platomav CPUMicrocodes** &mdash; the [platomav/CPUMicrocodes](https://github.com/platomav/CPUMicrocodes)
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
family19_cpuidA20F12_rev0A201210_date20240611_enc00_sha1a2b3c4d5e6f.bin
```

The fields encode the CPU family, CPU ID, update revision, build date,
encryption flag (when present) and the first 12 hex digits of the patch's
SHA-256 hash.
