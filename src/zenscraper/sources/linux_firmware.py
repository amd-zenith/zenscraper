#!/usr/bin/env python
'''
Linux firmware repository is a source of uCode container files.
'''

import shutil
import git
from git import Repo, Commit
from pathlib import Path
from rich.console import Console
from amd_ucode_container.extract import container_extract
from zenscraper.helpers import ucode_patch_process

REPO_URL = "https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git"


def _clone_repo(console: Console, dir: Path) -> Repo:
    # Create a folder for the repo if it does not exist...
    repo_dir = dir / "linux-firmware"
    repo_dir.mkdir(parents=True, exist_ok=True)
    # Check if the repo was cloned, if not, clone it, otherwise just use the folder
    try:
        repo = Repo(repo_dir)
        console.log("The linux-firmware repo was already cloned!")
    except git.InvalidGitRepositoryError:
        console.log("Cloning linux-firmware repo...")
        repo = Repo.clone_from(REPO_URL, repo_dir)
    # Return a valid repo object
    return repo


def _get_amd_ucode_commits(repo: Repo):
    return list(repo.iter_commits(paths='amd-ucode/'))


def _get_amd_ucode(workdir: Path, tmpdir: Path, repo: Repo, commit: Commit):
    # Create a folder if it does not exist...
    ucode_dir = tmpdir / commit.hexsha
    ucode_dir.mkdir(parents=True, exist_ok=True)
    # Go to the commit
    repo.git.checkout(commit.hexsha, force=True)
    # Copy files
    shutil.copytree(str(workdir / "cache" / "linux-firmware" / "amd-ucode"), str(ucode_dir), dirs_exist_ok=True)


def _process_container(container: Path, tmpdir: Path, outdir: Path) -> int:
    # Create a patches dir...
    patchdir = tmpdir / f"{container.name}_extracted/"
    patchdir.mkdir(parents=True, exist_ok=True)

    # Extract the container
    container_extract(container, patchdir)

    # Process all patches
    patches = list(patchdir.glob("*.bin"))
    for patch in patches:
        ucode_patch_process(patch, outdir)

    # Remove the patches dir...
    if patchdir.exists():
        shutil.rmtree(patchdir)

    return len(patches)

def linux_firmware_scrape(console: Console, workdir: Path, outdir: Path):
    cachedir = workdir / "cache"
    tmpdir = workdir / "tmp"

    console.log("Scraping the Linux firmware repository...")
    repo = _clone_repo(console, cachedir)

    console.log("Force-sync linux-firmware repo to origin/main (discarding local changes)...")
    repo.git.checkout("main", force=True)
    repo.git.reset("--hard")
    repo.git.clean("-fd")
    repo.git.fetch("origin", "main")
    repo.git.reset("--hard", "origin/main")

    console.log("Obtaining the git history for amd-ucode files...")
    commits = _get_amd_ucode_commits(repo)
    console.log(f"Found {len(commits)} relevant commits!")

    console.log("Obtaining all firmware containers...")
    containersdir = tmpdir / "ucode-containers"
    if containersdir.exists():
        shutil.rmtree(containersdir)
    containersdir.mkdir(parents=True, exist_ok=True)
    for commit in commits:
        console.log(f"Fetching commit {commit.hexsha}...")
        _get_amd_ucode(workdir, containersdir, repo, commit)

    containers = list(containersdir.glob("**/*.bin"))
    console.log(f"Extracting {len(containers)} uCode containers...")
    patchnum = 0
    for container in containers:
        patchnum += _process_container(container, tmpdir, outdir)
    console.log(f"Processed {patchnum} uCode patches!")

    if tmpdir.exists():
        shutil.rmtree(tmpdir)

    console.log("The linux-firmware source has been processed!")
