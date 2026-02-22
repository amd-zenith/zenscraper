#!/usr/bin/env python
'''
https://github.com/platomav/CPUMicrocodes
'''

import git
from git import Repo
from pathlib import Path
from rich.console import Console
from ..helpers import ucode_patch_process

REPO_URL = "https://github.com/platomav/CPUMicrocodes.git"


def _clone_repo(console: Console, dir: Path) -> Repo:
    # Create a folder for the repo if it does not exist...
    repo_dir = dir / "CPUMicrocodes"
    repo_dir.mkdir(parents=True, exist_ok=True)
    # Check if the repo was cloned, if not, clone it, otherwise just use the folder
    try:
        repo = Repo(repo_dir)
        console.log("The CPUMicrocodes repo was already cloned!")
    except git.InvalidGitRepositoryError:
        console.log("Cloning CPUMicrocodes repo...")
        repo = Repo.clone_from(REPO_URL, repo_dir)
    # Return a valid repo object
    return repo


def platomav_cpumicrocodes_scrape(console: Console, workdir: Path, outdir: Path):
    cachedir = workdir / "cache"
    repo_dir = cachedir / "CPUMicrocodes"

    console.log("Scraping the platomav CPUMicrocodes repository...")
    repo = _clone_repo(console, cachedir)

    console.log("Checkout main and ensure we are up to date...")
    repo.git.checkout("master")
    repo.git.pull()

    console.log("Obtaining all uCode patches...")
    patches = list(repo_dir.glob("AMD/*.bin"))
    for patch in patches:
        ucode_patch_process(patch, outdir)
    console.log(f"Processed {len(patches)} uCode patches!")

    console.log("The platomav CPUMicrocodes source has been processed!")
