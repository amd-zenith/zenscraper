#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later

import shutil
from abc import abstractmethod
from pathlib import Path
from zenscraper.catalog import Catalog, intern
from zenscraper.sources.abstract_source import AbstractSource
from git import Repo, Commit, InvalidGitRepositoryError
from rich.console import Console

class AbstractGitSource(AbstractSource):
    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def repo_url(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def repo_branch(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def repo_path(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def _scrape_commit(self, console: Console, repo_dir: Path, commitdir: Path, commit: Commit):
        '''
        Scrape the repo_dir for the given commit and store the relevant files in
        commitdir, which is the collection folder set aside for this commit.
        '''
        raise NotImplementedError()

    @abstractmethod
    def _scrape_collection(self, console: Console, collectdir: Path, outdir: Path, catalog: Catalog):
        '''
        Process the files in collectdir and store the relevant uCode patches in outdir.
        Return the number of uCode patches processed.
        '''
        raise NotImplementedError()

    def _repo_folder(self) -> str:
        repo_url = self.repo_url.rstrip("/")
        # Support URL forms like https://host/org/repo.git and git@host:org/repo.git.
        if ":" in repo_url and "://" not in repo_url:
            repo_name = repo_url.rsplit(":", 1)[-1]
        else:
            repo_name = repo_url.rsplit("/", 1)[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        if not repo_name:
            raise ValueError(f"Could not infer repository folder from URL: {self.repo_url}")
        return repo_name

    def _clone_repo(self, console: Console, repo_dir: Path) -> Repo:
        # Create a folder for the repo if it does not exist...
        repo_dir.mkdir(parents=True, exist_ok=True)
        # Check if the repo was cloned, if not, clone it, otherwise just use the folder
        try:
            repo = Repo(repo_dir)
            console.log(f"The {self.source_name} repo was already cloned!")
        except InvalidGitRepositoryError:
            console.log(f"Cloning {self.source_name} repo...")
            repo = Repo.clone_from(self.repo_url, repo_dir)
        # Return a valid repo object
        return repo

    def _force_sync(self, console: Console, repo: Repo):
        console.log(f"Force-sync {self.source_name} repo to origin/{self.repo_branch} (discarding local changes)...")
        repo.git.checkout(self.repo_branch, force=True)
        repo.git.reset("--hard")
        repo.git.clean("-fd")
        repo.git.fetch("origin", self.repo_branch)
        repo.git.reset("--hard", f"origin/{self.repo_branch}")


    def _get_commits(self, console: Console, repo: Repo):
        console.log(f"Obtaining the git history for {self.repo_path} files...")
        commits = list(repo.iter_commits(paths=self.repo_path))
        console.log(f"Found {len(commits)} relevant commits!")
        return commits

    def _commit_dir(self, collectdir: Path, commit: Commit) -> Path:
        '''
        The folder a commit's files are collected under. Naming it after the
        commit is what lets a collected file be traced back to the commit it
        came from once the whole history has been walked.
        '''
        return collectdir / commit.hexsha

    def _locate(self, collectdir: Path, path: Path) -> tuple[str, str, str]:
        '''
        Trace a collected file back to where it came from: the commit that
        carried it, that commit's date, and the path it has in the repo.
        '''
        commit_dir, *rest = path.relative_to(collectdir).parts
        # The files of a commit are collected from the watched path of the repo,
        # which their collected paths are relative to.
        repo_path = "/".join([self.repo_path.strip("/"), *rest])
        return intern(commit_dir), intern(self._commit_dates[commit_dir]), intern(repo_path)

    def _scrape(self, console: Console, cachedir: Path, tmpdir: Path, outdir: Path, catalog: Catalog):
        repo_dir = cachedir / self._repo_folder()
        repo = self._clone_repo(console, repo_dir)
        self._force_sync(console, repo)
        head = repo.head.commit.hexsha
        commits = self._get_commits(console, repo)
        catalog.record_source(
            self.source_id,
            name=self.source_name,
            repo_url=self.repo_url,
            branch=self.repo_branch,
            path=self.repo_path,
            head=head,
            commits_walked=len(commits),
        )
        self._commit_dates = {c.hexsha: c.committed_datetime.isoformat() for c in commits}
        collectdir = tmpdir / self._repo_folder()
        if collectdir.exists():
            shutil.rmtree(collectdir)
        collectdir.mkdir(parents=True, exist_ok=True)
        for commit in commits:
            console.log(f"Fetching commit {commit.hexsha}...")
            repo.git.checkout(commit.hexsha, force=True)
            commitdir = self._commit_dir(collectdir, commit)
            commitdir.mkdir(parents=True, exist_ok=True)
            self._scrape_commit(console, repo_dir, commitdir, commit)
        patchnum = self._scrape_collection(console, collectdir, outdir, catalog)
        if collectdir.exists():
            shutil.rmtree(collectdir)
        return patchnum
