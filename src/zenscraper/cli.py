#!/usr/bin/env python
'''
A command line tool to print information about an AMD uCode patch files.
'''

import argparse
from pathlib import Path
from rich.console import Console
from zenscraper.sources.linux_firmware_source import LinuxFirmwareSource
from zenscraper.sources.platomav_cpumicrocodes_source import PlatomavCpumicrocodesSource

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

    for s in sources:
        s.scrape(console, args.workdir, args.outdir)

    patchnum = len(list((args.outdir / "patches").glob("*.bin")))
    console.log(f"Now you have {patchnum} uCode patches to deal with!")


if __name__ == "__main__":
    main()
