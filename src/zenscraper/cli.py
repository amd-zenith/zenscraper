#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
'''
A command line tool to collect AMD uCode patch files.
'''

import argparse
from pathlib import Path
from rich.console import Console
from zenscraper.catalog import Catalog
from zenscraper.sources.linux_firmware_source import LinuxFirmwareSource
from zenscraper.sources.platomav_cpumicrocodes_source import PlatomavCpumicrocodesSource
from zenscraper.utils.naming import normalize_patch_names

BANNER = r'''
  ______           _____                                
 |___  /          / ____|                               
    / / ___ _ __ | (___   ___ _ __ __ _ _ __   ___ _ __ 
   / / / _ \ '_ \ \___ \ / __| '__/ _` | '_ \ / _ \ '__|
  / /_|  __/ | | |____) | (__| | | (_| | |_) |  __/ |   
 /_____\___|_| |_|_____/ \___|_|  \__,_| .__/ \___|_|   
                                       | |              
                                       |_|              
'''


def main():
    parser = argparse.ArgumentParser(description="A command line tool to collect AMD uCode!")
    parser.add_argument("--workdir", "-w", type=Path, default=Path.cwd() / "workdir", help="Directory for temporary files")
    parser.add_argument("--outdir", "-o", type=Path, default=Path.cwd(), help="Directory where scraped content will be stored")
    args = parser.parse_args()

    console = Console()
    console.print(BANNER, highlight=False)

    sources = [
        LinuxFirmwareSource(),
        PlatomavCpumicrocodesSource(),
    ]

    # Provenance is observed rather than computed, so a run adds to the record
    # earlier runs built up instead of starting it over.
    catalog_path = args.outdir / "catalog.json"
    catalog = Catalog.load(catalog_path)
    if catalog.patch_count:
        console.log(f"Picked up a provenance catalog of {catalog.patch_count} uCode patches!")

    fixed = normalize_patch_names(console, args.outdir, catalog)
    if fixed:
        console.log(f"Brought {fixed} stored uCode patches up to the current naming standard!")

    for s in sources:
        s.scrape(console, args.workdir, args.outdir, catalog)

    # Patches stored by an earlier run that no source claimed this time are
    # still part of the collection, so the catalog accounts for them too.
    catalog.sweep(console, args.outdir / "patches")
    catalog.save(catalog_path)

    patchnum = len(list((args.outdir / "patches").glob("*.bin")))
    console.log(f"Now you have {patchnum} uCode patches to deal with!")
    console.log(f"Their provenance catalog records {catalog.sighting_count} sightings upstream!")


if __name__ == "__main__":
    main()
