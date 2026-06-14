#!/usr/bin/env python
'''
https://github.com/platomav/CPUMicrocodes
'''

import git
import shutil
from git import Repo, Commit
from pathlib import Path
from rich.console import Console
from zenscraper.helpers import ucode_patch_process

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


def _get_amd_commits(repo: Repo):
    return list(repo.iter_commits(paths='AMD/'))


def _get_amd_patches(workdir: Path, tmpdir: Path, repo: Repo, commit: Commit):
    # Create a folder for this commit if it does not exist...
    patch_dir = tmpdir / commit.hexsha
    patch_dir.mkdir(parents=True, exist_ok=True)
    # Go to the commit
    repo.git.checkout(commit.hexsha, force=True)
    # Copy patches from this snapshot
    shutil.copytree(str(workdir / "cache" / "CPUMicrocodes" / "AMD"), str(patch_dir), dirs_exist_ok=True)


def platomav_cpumicrocodes_scrape(console: Console, workdir: Path, outdir: Path):
    cachedir = workdir / "cache"
    tmpdir = workdir / "tmp"

    console.log("Scraping the platomav CPUMicrocodes repository...")
    repo = _clone_repo(console, cachedir)

    console.log("Force-sync CPUMicrocodes repo to origin/master (discarding local changes)...")
    repo.git.checkout("master", force=True)
    repo.git.reset("--hard")
    repo.git.clean("-fd")
    repo.git.fetch("origin", "master")
    repo.git.reset("--hard", "origin/master")

    console.log("Obtaining the git history for AMD patches...")
    commits = _get_amd_commits(repo)
    console.log(f"Found {len(commits)} relevant commits!")

    console.log("Collecting all AMD patches from commit history...")
    patchesdir = tmpdir / "platomav-amd-patches"
    if patchesdir.exists():
        shutil.rmtree(patchesdir)
    patchesdir.mkdir(parents=True, exist_ok=True)
    for commit in commits:
        console.log(f"Fetching commit {commit.hexsha}...")
        _get_amd_patches(workdir, patchesdir, repo, commit)

    console.log("Obtaining all uCode patches...")
    patches = list(patchesdir.glob("**/*.bin"))
    for patch in patches:
        ucode_patch_process(patch, outdir)
    console.log(f"Processed {len(patches)} uCode patches!")

    if tmpdir.exists():
        shutil.rmtree(tmpdir)

    console.log("The platomav CPUMicrocodes source has been processed!")
