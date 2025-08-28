#!/usr/bin/env python
# coding: utf-8

import logging
import os
from typing import Dict, List, Optional, Tuple, Any

from k3handy import cmdf
from k3handy import parse_flag
from k3handy import pabs
from k3str import to_utf8

logger = logging.getLogger(__name__)


class Git(object):
    """Git command wrapper with configurable paths and options."""

    def __init__(
        self,
        opt: Any,
        gitpath: Optional[str] = None,
        gitdir: Optional[str] = None,
        working_dir: Optional[str] = None,
        cwd: Optional[str] = None,
        ctxmsg: Optional[str] = None,
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

    # high level API

    def checkout(self, branch: str, flag: str = "x") -> Any:
        """Checkout specified branch."""
        return self.cmdf("checkout", branch, flag=flag)

    def fetch(self, name: str, flag: str = "") -> Any:
        """Fetch from remote repository."""
        return self.cmdf("fetch", name, flag=flag)

    def add(self, *files: str, update: bool = False, flag: str = "x") -> Any:
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

    def commit(self, message, flag="x"):
        """Commit staged changes with message.

        Args:
            message: Commit message (required)
            flag: Command execution flags

        Returns:
            str: Commit hash of new commit
        """
        self.cmdf("commit", "-m", message, flag=flag)
        return self.cmdf("rev-parse", "HEAD", flag=flag + "n0")

    def reset_to_commit(
        self, mode: str, target: Optional[str] = None, flag: str = "x"
    ) -> Any:
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

    # branch

    def branch_default_remote(self, branch: str, flag: str = "") -> Any:
        """Get default remote name for branch."""
        return self.cmdf(
            "config", "--get", "branch.{}.remote".format(branch), flag=flag + "n0"
        )

    def branch_default_upstream(self, branch: str, flag: str = "") -> Any:
        """Get upstream branch name (e.g., origin/master for master)."""
        return self.cmdf(
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            branch + "@{upstream}",
            flag=flag + "n0",
        )

    def branch_set(self, branch: str, rev: str, flag: str = "x") -> None:
        """Set branch reference to specified revision."""

        self.cmdf("update-ref", "refs/heads/{}".format(branch), rev, flag=flag)

    def branch_list(self, scope: str = "local", flag: str = "") -> List[str]:
        """List branches in specified scope."""

        refs = self.ref_list(flag=parse_flag(flag))

        res = []
        if scope == "local":
            pref = "refs/heads/"
            for ref in refs.keys():
                if ref.startswith(pref):
                    res.append(ref[len(pref) :])

        return sorted(res)

    def branch_common_base(self, branch: str, other: str, flag: str = "") -> Any:
        """Find merge base commit of two branches."""

        return self.cmdf("merge-base", branch, other, flag=flag + "0")

    def branch_divergency(
        self, branch: str, upstream: Optional[str] = None, flag: str = ""
    ) -> Tuple[Any, Any, Any]:
        """Get divergency between branch and upstream.

        Returns:
            tuple: (base_commit, branch_commits, upstream_commits)
        """

        if upstream is None:
            upstream = self.branch_default_upstream(branch, flag="x")

        base = self.branch_common_base(branch, upstream, flag="x")

        b_logs = self.cmdf("log", "--format=%H", base + ".." + branch, flag="xo")
        u_logs = self.cmdf("log", "--format=%H", base + ".." + upstream, flag="xo")

        return (base, b_logs, u_logs)

    # head

    def head_branch(self, flag: str = "") -> Any:
        """Get current branch name."""
        return self.cmdf("symbolic-ref", "--short", "HEAD", flag=flag + "n0")

    # remote

    def remote_get(self, name: str, flag: str = "") -> Any:
        """Get URL for remote."""
        return self.cmdf("remote", "get-url", name, flag=flag + "n0")

    def remote_add(self, name: str, url: str, flag: str = "x", **options: Any) -> None:
        """Add remote with name and URL."""
        self.cmdf("remote", "add", name, url, **options, flag=flag)

    # blob

    def blob_new(self, f: str, flag: str = "") -> Any:
        """Create new blob from file."""
        return self.cmdf("hash-object", "-w", f, flag=flag + "n0")

    #  tree

    def tree_of(self, commit: str, flag: str = "") -> Any:
        """Get tree hash of commit."""
        return self.cmdf("rev-parse", commit + "^{tree}", flag=flag + "n0")

    def tree_commit(
        self,
        treeish: str,
        commit_message: str,
        parent_commits: List[str],
        flag: str = "x",
    ) -> Any:
        """Create commit from tree with message and parents."""

        parent_args = []
        for c in parent_commits:
            parent_args.extend(["-p", c])

        return self.cmdf(
            "commit-tree", treeish, *parent_args, input=commit_message, flag=flag + "n0"
        )

    def tree_items(
        self,
        treeish: str,
        name_only: bool = False,
        with_size: bool = False,
        flag: str = "x",
    ) -> Any:
        """List items in tree."""
        args = []
        if name_only:
            args.append("--name-only")

        if with_size:
            args.append("--long")
        return self.cmdf("ls-tree", treeish, *args, flag=flag + "no")

    def tree_add_obj(self, cur_tree: str, path: str, treeish: str) -> Any:
        """Add object to tree at specified path."""

        sep = os.path.sep

        itms = self.tree_items(cur_tree)

        if sep not in path:
            return self.tree_new_replace(itms, path, treeish, flag="x")

        # a/b/c -> a, b/c
        p0, left = path.split(sep, 1)
        p0item = self.tree_find_item(cur_tree, fn=p0, typ="tree")

        if p0item is None:
            newsubtree = treeish
            for p in reversed(left.split(sep)):
                newsubtree = self.tree_new_replace([], p, newsubtree, flag="x")
        else:
            subtree = p0item["object"]
            newsubtree = self.tree_add_obj(subtree, left, treeish)

        return self.tree_new_replace(itms, p0, newsubtree, flag="x")

    def tree_find_item(
        self, treeish: str, fn: Optional[str] = None, typ: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """Find item in tree by filename and/or type."""
        for itm in self.tree_items(treeish):
            itm = self.treeitem_parse(itm)
            if fn is not None and itm["fn"] != fn:
                continue
            if typ is not None and itm["type"] != typ:
                continue

            return itm
        return None

    def treeitem_parse(self, line: str) -> Dict[str, str]:
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

    def tree_new(self, itms: List[str], flag: str = "x") -> Any:
        """Create new tree from items."""

        treeish = self.cmdf("mktree", input="\n".join(itms), flag=flag + "n0")
        return treeish

    def tree_new_replace(
        self,
        itms: List[str],
        name: str,
        obj: str,
        mode: Optional[str] = None,
        flag: str = "x",
    ) -> Any:
        """Create new tree replacing/adding item."""

        new_items = self.treeitems_replace_item(itms, name, obj, mode=mode)

        new_treeish = self.cmdf("mktree", input="\n".join(new_items), flag=flag + "n0")
        return new_treeish

    def treeitems_replace_item(
        self, itms: List[str], name: str, obj: Optional[str], mode: Optional[str] = None
    ) -> List[str]:
        """Replace item in tree items list."""

        new_items = [x for x in itms if self.treeitem_parse(x)["fn"] != name]

        if obj is not None:
            itm = self.treeitem_new(name, obj, mode=mode)
            new_items.append(itm)

        return new_items

    # treeitem

    def treeitem_new(self, name: str, obj: str, mode: Optional[str] = None) -> str:
        """Create new tree item string."""

        typ = self.obj_type(obj, flag="x")
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

    def ref_list(self, flag: str = "") -> Dict[str, str]:
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
        hash_and_refs = self.cmdf("show-ref", flag=parse_flag("xo", flag))

        res = {}
        for line in hash_and_refs:
            hsh, ref = line.strip().split()

            res[ref] = hsh

        return res

    # rev

    def rev_of(self, name: str, flag: str = "") -> Optional[str]:
        """Get SHA hash of object.

        Args:
            name: Hash, ref name, or branch name
            flag: 'x' to raise on error, '' to return None

        Returns:
            str: SHA hash or None if not found
        """
        return self.cmdf("rev-parse", "--verify", "--quiet", name, flag=flag + "n0")

    def obj_type(self, obj: str, flag: str = "") -> Any:
        """Get object type (blob, tree, commit, tag)."""
        return self.cmdf("cat-file", "-t", obj, flag=flag + "n0")

    # wrapper of cli

    def _opt(self, **kwargs: Any) -> Dict[str, Any]:
        """Build command options dict."""
        opt = {}
        if self.cwd is not None:
            opt["cwd"] = self.cwd
        opt.update(kwargs)
        return opt

    def _args(self) -> List[str]:
        """Get git command arguments."""
        return self.opt.to_args()

    def cmdf(self, *args: str, flag: str = "", **kwargs: Any) -> Any:
        """Execute git command with configured options."""
        return cmdf(
            self.gitpath, *self._args(), *args, flag=flag, **self._opt(**kwargs)
        )

    def out(self, fd: int, *msg: str) -> None:
        """Write formatted output to file descriptor."""
        if self.ctxmsg is not None:
            os.write(fd, to_utf8(self.ctxmsg) + b": ")

        for i, m in enumerate(msg):
            os.write(fd, to_utf8(m))
            if i != len(msg) - 1:
                os.write(fd, b" ")
        os.write(fd, b"\n")
