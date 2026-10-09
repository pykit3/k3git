from __future__ import annotations

import logging
import os
from typing import Any

from k3handy import CMD_RAISE_STDOUT, CmdFlag, cmdf, pabs, parse_flag
from k3str import to_utf8

logger = logging.getLogger(__name__)


class Git:
    """Git command wrapper with configurable paths and options."""

    def __init__(
        self,
        opt: Any,
        gitpath: str | None = None,
        gitdir: str | None = None,
        working_dir: str | None = None,
        cwd: str | None = None,
        ctxmsg: str | None = None,
    ) -> None:
        """Initialize Git wrapper.

        Args:
            opt: Command options object with clone() method
            gitpath: Path to git executable
            gitdir: Git directory path (overrides -C option)
            working_dir: Working tree path (overrides -C option)
            cwd: Current working directory for commands
            ctxmsg: Context message prefix for output
        """
        self.opt = opt.clone()
        # gitdir and working_dir is specified and do not consider '-C' option
        if gitdir is not None:
            self.opt.opt["git_dir"] = pabs(gitdir)
        if working_dir is not None:
            self.opt.opt["work_tree"] = pabs(working_dir)

        self.cwd = cwd

        self.gitpath = gitpath or "git"
        self.ctxmsg = ctxmsg

    # repo

    def repo_root(self, flag: str = "") -> str | None:
        """Get repository root directory path.

        Args:
            flag: Command execution flags

        Returns:
            str: Absolute path to repository root, or None if not in a git repo

        Examples:
            >>> git.repo_root()
            '/Users/user/project'
            >>> git.repo_root(flag=CmdFlag.RAISE)  # Raises if not in git repo
        """
        return self.cmdf("rev-parse", "--show-toplevel", flag=parse_flag(flag, ["none", "oneline"]))

    def repo_is_repository(self, path: str | None = None) -> bool:
        """Check if path is a git repository.

        Args:
            path: Directory path to check (None = current directory)

        Returns:
            bool: True if path contains .git directory or file

        Examples:
            >>> git.repo_is_repository('/path/to/repo')
            True
            >>> git.repo_is_repository('/path/to/non-repo')
            False
            >>> git.repo_is_repository()  # Check current directory
            True
        """
        if path is None:
            check_path = self.cwd if self.cwd is not None else os.getcwd()
        else:
            check_path = path

        git_path = os.path.join(check_path, ".git")
        return os.path.exists(git_path)

    # high level API

    def checkout(self, branch: str, flag: str | list[str] = CmdFlag.RAISE) -> Any:
        """Checkout specified branch."""
        return self.cmdf("checkout", branch, flag=flag)

    def fetch(self, name: str, flag: str = "") -> Any:
        """Fetch from remote repository."""
        return self.cmdf("fetch", name, flag=flag)

    def fetch_url(self, url: str, refspec: str, no_tags: bool = True, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Fetch refspec from URL without adding remote.

        Args:
            url: Git repository URL
            refspec: Refspec to fetch (e.g., 'refs/heads/master:refs/remotes/origin/master')
            no_tags: If True, don't fetch tags (default: True)
            flag: Command execution flags

        Examples:
            >>> git.fetch_url('https://github.com/user/repo.git',
            ...               'refs/heads/main:refs/remotes/tmp/main')
            >>> git.fetch_url('git@github.com:user/repo.git',
            ...               '+refs/heads/*:refs/remotes/mirror/*',
            ...               no_tags=False)

        Raises:
            ValueError: If url or refspec is empty
            CalledProcessError: If fetch fails
        """
        if not url:
            raise ValueError("url cannot be empty")
        if not refspec:
            raise ValueError("refspec cannot be empty")

        args = ["fetch"]
        if no_tags:
            args.append("--no-tags")
        args.extend([url, refspec])

        self.cmdf(*args, flag=flag)

    def add(self, *files: str, update: bool = False, flag: str | list[str] = CmdFlag.RAISE) -> Any:
        """Add files to staging area.

        Args:
            *files: Files or patterns to add (required unless update=True)
            update: If True, add -u flag to update tracked files only
            flag: Command execution flags

        Examples:
            git.add('file.txt')          # git add file.txt
            git.add('\\*.py', 'docs/')     # git add \\*.py docs/
            git.add(update=True)         # git add -u (updates all tracked files)
            git.add('src/', update=True) # git add -u src/

        Raises:
            ValueError: If no files provided and update=False
        """
        if not files and not update:
            raise ValueError("Must specify files to add or use update=True")

        args = []
        if update:
            args.append("-u")
        args.extend(files)

        return self.cmdf("add", *args, flag=flag)

    def commit(self, message, flag=CmdFlag.RAISE):
        """Commit staged changes with message.

        Args:
            message(str): Commit message (required)
            flag(str | list[str]): Command execution flags

        Returns:
            (str): Commit hash of new commit
        """
        self.cmdf("commit", "-m", message, flag=flag)
        return self.cmdf("rev-parse", "HEAD", flag=parse_flag(flag, ["none", "oneline"]))

    def reset_to_commit(self, mode: str, target: str | None = None, flag: str | list[str] = CmdFlag.RAISE) -> Any:
        """Reset HEAD to specified commit.

        Args:
            mode: Reset mode (soft, mixed, hard, merge, keep)
            target: Target commit (defaults to HEAD)
        """
        if target is None:
            target = "HEAD"

        return self.cmdf("reset", "--" + mode, target, flag=flag)

    # worktree

    def worktree_is_clean(self, flag: str = "") -> bool:
        """Check if working tree has no uncommitted changes."""
        # git bug:
        # Without running 'git status' first, "diff-index" in our test does not
        # pass
        self.cmdf("status", flag="")
        code, _out, _err = self.cmdf("diff-index", "--quiet", "HEAD", "--", flag=flag)
        return code == 0

    def worktree_staged_files(self, flag: str = "") -> list[str]:
        """Get list of files with staged changes.

        Args:
            flag: Command execution flags

        Returns:
            list: Filenames of staged files (empty list if nothing staged)

        Examples:
            >>> git.add('file1.txt', 'file2.txt')
            >>> git.worktree_staged_files()
            ['file1.txt', 'file2.txt']
            >>> git.worktree_staged_files()
            []  # Nothing staged
        """
        return self.cmdf("diff", "--name-only", "--cached", flag=parse_flag(flag, ["none", "stdout"]))

    # branch

    def branch_default_remote(self, branch: str, flag: str = "") -> Any:
        """Get default remote name for branch."""
        return self.cmdf("config", "--get", f"branch.{branch}.remote", flag=parse_flag(flag, ["none", "oneline"]))

    def branch_default_upstream(self, branch: str, flag: str = "") -> Any:
        """Get upstream branch name (e.g., origin/master for master)."""
        return self.cmdf(
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            branch + "@{upstream}",
            flag=parse_flag(flag, ["none", "oneline"]),
        )

    def branch_set(self, branch: str, rev: str, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Set branch reference to specified revision."""

        self.cmdf("update-ref", f"refs/heads/{branch}", rev, flag=flag)

    def branch_list(self, scope: str = "local", flag: str = "") -> list[str]:
        """List branches in specified scope."""

        refs = self.ref_list(flag=parse_flag(flag))

        res = []
        if scope == "local":
            pref = "refs/heads/"
            for ref in refs:
                if ref.startswith(pref):
                    res.append(ref[len(pref) :])

        return sorted(res)

    def branch_common_base(self, branch: str, other: str, flag: str = "") -> Any:
        """Find merge base commit of two branches."""

        return self.cmdf("merge-base", branch, other, flag=parse_flag(flag, ["oneline"]))

    def branch_divergency(self, branch: str, upstream: str | None = None, flag: str = "") -> tuple[Any, Any, Any]:
        """Get divergency between branch and upstream.

        Returns:
            tuple: (base_commit, branch_commits, upstream_commits)
        """

        if upstream is None:
            upstream = self.branch_default_upstream(branch, flag=CmdFlag.RAISE)

        base = self.branch_common_base(branch, upstream, flag=CmdFlag.RAISE)

        b_logs = self.cmdf("log", "--format=%H", base + ".." + branch, flag=CMD_RAISE_STDOUT)
        u_logs = self.cmdf("log", "--format=%H", base + ".." + upstream, flag=CMD_RAISE_STDOUT)

        return (base, b_logs, u_logs)

    def branch_rebase(self, upstream: str, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Rebase current branch onto upstream.

        Args:
            upstream: Branch or commit to rebase onto
            flag: Command execution flags

        Examples:
            >>> git.branch_rebase('master')
            >>> git.branch_rebase('origin/main')

        Raises:
            ValueError: If upstream is empty
            CalledProcessError: If rebase fails or conflicts occur
        """
        if not upstream:
            raise ValueError("upstream cannot be empty")

        self.cmdf("rebase", upstream, flag=flag)

    def branch_merge_ff(self, upstream: str | None = None, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Fast-forward merge upstream into current branch.

        Args:
            upstream: Branch to merge (None = tracking branch)
            flag: Command execution flags

        Examples:
            >>> git.branch_merge_ff('origin/master')
            >>> git.branch_merge_ff()  # Merges tracking branch

        Raises:
            ValueError: If upstream is empty string
            CalledProcessError: If fast-forward not possible or no tracking branch
        """
        if upstream == "":
            raise ValueError("upstream cannot be empty string (use None for default)")

        args = ["merge", "--no-edit", "--commit", "--ff-only"]
        if upstream is not None:
            args.append(upstream)

        self.cmdf(*args, flag=flag)

    # head

    def head_branch(self, flag: str = "") -> Any:
        """Get current branch name."""
        return self.cmdf("symbolic-ref", "--short", "HEAD", flag=parse_flag(flag, ["none", "oneline"]))

    # remote

    def remote_get(self, name: str, flag: str = "") -> Any:
        """Get URL for remote."""
        return self.cmdf("remote", "get-url", name, flag=parse_flag(flag, ["none", "oneline"]))

    def remote_add(self, name: str, url: str, flag: str | list[str] = CmdFlag.RAISE, **options: Any) -> None:
        """Add remote with name and URL."""
        self.cmdf("remote", "add", name, url, **options, flag=flag)

    def remote_push(self, remote: str, branch: str, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Push branch to remote.

        Args:
            remote: Remote name or URL
            branch: Branch name to push
            flag: Command execution flags

        Examples:
            >>> git.remote_push('origin', 'master')
            >>> git.remote_push('backup', 'develop')

        Raises:
            ValueError: If remote or branch is empty
            CalledProcessError: If push fails
        """
        if not remote:
            raise ValueError("remote cannot be empty")
        if not branch:
            raise ValueError("branch cannot be empty")

        self.cmdf("push", remote, branch, flag=flag)

    def remote_push_all(self, branch: str, flag: str | list[str] = CmdFlag.RAISE) -> dict[str, bool]:
        """Push branch to all configured remotes.

        Args:
            branch: Branch name to push
            flag: Command execution flags ('x' raises on ANY failure, '' continues on errors)

        Returns:
            dict: Map of remote name to success status (True/False)

        Examples:
            >>> git.remote_push_all('master')
            {'origin': True, 'backup': True}
            >>> git.remote_push_all('develop', flag='')  # Continue on errors
            {'origin': True, 'backup': False}  # backup failed but didn't raise

        Raises:
            ValueError: If branch is empty
            CalledProcessError: If flag=CmdFlag.RAISE and any push fails
        """
        if not branch:
            raise ValueError("branch cannot be empty")

        # Get all remotes
        from k3handy import CalledProcessError

        remotes_output = self.cmdf("remote", flag=CMD_RAISE_STDOUT)
        results = {}

        for remote in remotes_output:
            try:
                self.remote_push(remote, branch, flag=CmdFlag.RAISE)
                results[remote] = True
            except CalledProcessError:
                results[remote] = False
                if "raise" in parse_flag(flag):
                    raise

        return results

    # blob

    def blob_new(self, f: str, flag: str = "") -> Any:
        """Create new blob from file."""
        return self.cmdf("hash-object", "-w", f, flag=parse_flag(flag, ["none", "oneline"]))

    #  tree

    def tree_of(self, commit: str, flag: str = "") -> Any:
        """Get tree hash of commit."""
        return self.cmdf("rev-parse", commit + "^{tree}", flag=parse_flag(flag, ["none", "oneline"]))

    def tree_commit(
        self,
        treeish: str,
        commit_message: str,
        parent_commits: list[str],
        flag: str | list[str] = CmdFlag.RAISE,
    ) -> Any:
        """Create commit from tree with message and parents."""

        parent_args = []
        for c in parent_commits:
            parent_args.extend(["-p", c])

        return self.cmdf(
            "commit-tree", treeish, *parent_args, input=commit_message, flag=parse_flag(flag, ["none", "oneline"])
        )

    def tree_items(
        self,
        treeish: str,
        name_only: bool = False,
        with_size: bool = False,
        flag: str | list[str] = CmdFlag.RAISE,
    ) -> Any:
        """List items in tree."""
        # Without --full-tree, ls-tree run in a sub dir of the work tree lists
        # only the entries under that dir
        args = ["--full-tree"]
        if name_only:
            args.append("--name-only")

        if with_size:
            args.append("--long")
        return self.cmdf("ls-tree", treeish, *args, flag=parse_flag(flag, ["none", "stdout"]))

    def tree_add_obj(self, cur_tree: str, path: str, treeish: str) -> Any:
        """Add object to tree at specified path."""

        sep = os.path.sep

        itms = self.tree_items(cur_tree)

        if sep not in path:
            return self.tree_new_replace(itms, path, treeish, flag=CmdFlag.RAISE)

        # a/b/c -> a, b/c
        p0, left = path.split(sep, 1)
        p0item = self.tree_find_item(cur_tree, fn=p0, typ="tree")

        if p0item is None:
            newsubtree = treeish
            for p in reversed(left.split(sep)):
                newsubtree = self.tree_new_replace([], p, newsubtree, flag=CmdFlag.RAISE)
        else:
            subtree = p0item["object"]
            newsubtree = self.tree_add_obj(subtree, left, treeish)

        return self.tree_new_replace(itms, p0, newsubtree, flag=CmdFlag.RAISE)

    def tree_find_item(self, treeish: str, fn: str | None = None, typ: str | None = None) -> dict[str, str] | None:
        """Find item in tree by filename and/or type."""
        for itm in self.tree_items(treeish):
            itm = self.treeitem_parse(itm)
            if fn is not None and itm["fn"] != fn:
                continue
            if typ is not None and itm["type"] != typ:
                continue

            return itm
        return None

    def treeitem_parse(self, line: str) -> dict[str, str]:
        """Parse git ls-tree output line into dict.

        Example output formats:
            100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2    imsuperman
            040000 tree a668431ae444a5b68953dc61b4b3c30e066535a2    foo
        """

        # git-ls-tree output:
        #     <mode> SP <type> SP <object> TAB <file>
        # This output format is compatible with what --index-info --stdin of git update-index expects.
        # When the -l option is used, format changes to
        #     <mode> SP <type> SP <object> SP <object size> TAB <file>
        # E.g.:
        # 100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2    imsuperman
        # 040000 tree a668431ae444a5b68953dc61b4b3c30e066535a2    foo

        p, fn = line.split("\t", 1)

        elts = p.split()
        rst = {
            "mode": elts[0],
            "type": elts[1],
            "object": elts[2],
            "fn": fn,
        }
        if len(elts) == 4:
            rst["size"] = elts[3]

        return rst

    def tree_new(self, itms: list[str], flag: str | list[str] = CmdFlag.RAISE) -> Any:
        """Create new tree from items."""

        treeish = self.cmdf("mktree", input="\n".join(itms), flag=parse_flag(flag, ["none", "oneline"]))
        return treeish

    def tree_new_replace(
        self,
        itms: list[str],
        name: str,
        obj: str,
        mode: str | None = None,
        flag: str | list[str] = CmdFlag.RAISE,
    ) -> Any:
        """Create new tree replacing/adding item."""

        new_items = self.treeitems_replace_item(itms, name, obj, mode=mode)

        new_treeish = self.cmdf("mktree", input="\n".join(new_items), flag=parse_flag(flag, ["none", "oneline"]))
        return new_treeish

    def treeitems_replace_item(self, itms: list[str], name: str, obj: str | None, mode: str | None = None) -> list[str]:
        """Replace item in tree items list."""

        new_items = [x for x in itms if self.treeitem_parse(x)["fn"] != name]

        if obj is not None:
            itm = self.treeitem_new(name, obj, mode=mode)
            new_items.append(itm)

        return new_items

    # treeitem

    def treeitem_new(self, name: str, obj: str, mode: str | None = None) -> str:
        """Create new tree item string."""

        typ = self.obj_type(obj, flag=CmdFlag.RAISE)
        item_fmt = "{mode} {typ} {object}\t{name}"

        if typ == "tree":
            mod = "040000"
        else:
            if mode is None:
                mod = "100644"
            else:
                mod = mode

        itm = item_fmt.format(mode=mod, typ=typ, object=obj, name=name)
        return itm

    # ref

    def ref_list(self, flag: str = "") -> dict[str, str]:
        """List all refs.

        Returns:
            dict: Map of ref names(such as ``refs/heads/master``) to commit hashes

        Example output:
            46f1130da3d74edf5ef0961718c9afc47ad28a44 refs/heads/master
            104403398142d4643669be8099697a6b51bbbc62 refs/remotes/origin/HEAD
        """

        #  git show-ref
        #  46f1130da3d74edf5ef0961718c9afc47ad28a44 refs/heads/master
        #  104403398142d4643669be8099697a6b51bbbc62 refs/remotes/origin/HEAD
        #  46f1130da3d74edf5ef0961718c9afc47ad28a44 refs/remotes/origin/fixup
        #  104403398142d4643669be8099697a6b51bbbc62 refs/remotes/origin/master
        #  4a90cdaec2e7bb945c9a49148919db0a6ffa059d refs/tags/v0.1.0
        #  b1af433f3291ff137679ad3889be5d72377f0cb6 refs/tags/v0.1.10
        hash_and_refs = self.cmdf("show-ref", flag=parse_flag(["raise", "stdout"], flag))

        res = {}
        for line in hash_and_refs:
            hsh, ref = line.strip().split()

            res[ref] = hsh

        return res

    def ref_delete(self, ref: str, flag: str | list[str] = CmdFlag.RAISE) -> None:
        """Delete a git reference.

        Args:
            ref: Reference to delete (e.g., 'refs/heads/branch', 'refs/tags/v1.0')
            flag: Command execution flags

        Examples:
            >>> git.ref_delete('refs/heads/feature-branch')
            >>> git.ref_delete('refs/tags/old-tag')

        Raises:
            ValueError: If ref is empty
            CalledProcessError: If deletion fails
        """
        if not ref:
            raise ValueError("ref cannot be empty")

        self.cmdf("update-ref", "-d", ref, flag=flag)

    # rev

    def rev_of(self, name: str, flag: str = "") -> str | None:
        """Get SHA hash of object.

        Args:
            name: Hash, ref name, or branch name
            flag: 'x' to raise on error, '' to return None

        Returns:
            str: SHA hash or None if not found
        """
        return self.cmdf("rev-parse", "--verify", "--quiet", name, flag=parse_flag(flag, ["none", "oneline"]))

    def obj_type(self, obj: str, flag: str = "") -> Any:
        """Get object type (blob, tree, commit, tag)."""
        return self.cmdf("cat-file", "-t", obj, flag=parse_flag(flag, ["none", "oneline"]))

    # log

    def log_date(self, ref: str, format: str = "%ad", flag: str = "") -> str | None:
        """Get date from commit log.

        Args:
            ref: Commit reference (hash, branch, tag, etc.)
            format: Date format string (default: %ad for author date)
                    Common formats:
                    - %ad: author date
                    - %cd: committer date
                    - %ai: author date (ISO 8601)
                    - %ci: committer date (ISO 8601)
            flag: Command execution flags

        Returns:
            str: Formatted date string, or None if ref not found

        Examples:
            >>> git.log_date('HEAD')
            'Mon Aug 14 20:47:31 2023 +0800'
            >>> git.log_date('master', format='%ai')
            '2023-08-14 20:47:31 +0800'
            >>> git.log_date('nonexistent')
            None

        Raises:
            ValueError: If ref is empty string
        """
        if not ref:
            raise ValueError("ref cannot be empty")

        return self.cmdf("log", "-1", "--format=" + format, ref, flag=parse_flag(flag, ["none", "oneline"]))

    def log_grep(
        self,
        pattern: str,
        grep_type: str = "grep",
        max_count: int | None = None,
        flag: str = "",
    ) -> list[str]:
        """Find commits matching grep pattern.

        Args:
            pattern: Pattern to search for
            grep_type: Type of grep ('grep' for message, 'G' for content, 'S' for pickaxe)
            max_count: Limit number of results (None = unlimited)
            flag: Command execution flags

        Returns:
            list: Commit hashes matching pattern (newest first), empty list if none found

        Examples:
            >>> git.log_grep('fix bug')  # Search commit messages
            ['abc123...', 'def456...']
            >>> git.log_grep('TODO', grep_type='G')  # Search file contents
            ['ghi789...']
            >>> git.log_grep('squash', max_count=1)  # Get latest matching commit
            ['abc123...']

        Raises:
            ValueError: If pattern is empty or grep_type invalid or max_count < 1
        """
        if not pattern:
            raise ValueError("pattern cannot be empty")

        if grep_type not in ("grep", "G", "S", "author", "committer"):
            raise ValueError(f"Invalid grep_type: {grep_type}")

        args = ["log", f"--{grep_type}={pattern}", "--format=%H"]
        if max_count is not None:
            if max_count < 1:
                raise ValueError("max_count must be >= 1")
            args.append(f"--max-count={max_count}")

        return self.cmdf(*args, flag=parse_flag(flag, ["none", "stdout"]))

    # wrapper of cli

    def _opt(self, **kwargs: Any) -> dict[str, Any]:
        """Build command options dict."""
        opt = {}
        if self.cwd is not None:
            opt["cwd"] = self.cwd
        opt.update(kwargs)
        return opt

    def _args(self) -> list[str]:
        """Get git command arguments."""
        return self.opt.to_args()

    def cmdf(self, *args: str, flag: str = "", **kwargs: Any) -> Any:
        """Execute git command with configured options."""
        return cmdf(self.gitpath, *self._args(), *args, flag=flag, **self._opt(**kwargs))

    def out(self, fd: int, *msg: str) -> None:
        """Write formatted output to file descriptor."""
        if self.ctxmsg is not None:
            os.write(fd, to_utf8(self.ctxmsg) + b": ")

        for i, m in enumerate(msg):
            os.write(fd, to_utf8(m))
            if i != len(msg) - 1:
                os.write(fd, b" ")
        os.write(fd, b"\n")
