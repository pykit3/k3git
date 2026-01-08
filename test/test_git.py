import os
import shutil
import unittest

import k3ut
from k3fs import fread
from k3fs import fwrite
from k3git import Git
from k3git import GitOpt
from k3handy import CalledProcessError
from k3handy.cmdutil import cmd0
from k3handy.cmdutil import cmdf
from k3handy.cmdutil import cmdout
from k3handy.cmdutil import cmdx
from k3handy.path import pjoin

dd = k3ut.dd

this_base = os.path.dirname(__file__)

origit = "git"

superp = pjoin(this_base, "testdata", "super")
supergitp = pjoin(this_base, "testdata", "supergit")
wowgitp = pjoin(this_base, "testdata", "wowgit")
branch_test_git_p = pjoin(this_base, "testdata", "branch_test_git")
branch_test_worktree_p = pjoin(this_base, "testdata", "branch_test_worktree")


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        _clean_case()

        # .git can not be track in a git repo.
        # need to manually create it.
        fwrite(pjoin(this_base, "testdata", "super", ".git"), "gitdir: ../supergit")

    def tearDown(self):
        if os.environ.get("GIFT_NOCLEAN", None) == "1":
            return
        _clean_case()

    def _fcontent(self, txt, *ps):
        self.assertTrue(os.path.isfile(pjoin(*ps)), pjoin(*ps) + " should exist")

        actual = fread(pjoin(*ps))
        self.assertEqual(txt, actual, "check file content")


class TestGitInit(BaseTest):
    def test_init(self):
        g = Git(GitOpt(), gitdir=supergitp, working_dir=superp)
        g.checkout("master")
        self._fcontent("superman\n", superp, "imsuperman")

        self.assertRaises(CalledProcessError, g.checkout, "foo")


class TestGitRepo(BaseTest):
    def test_repo_root(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Success case - should return absolute path to repo root
        root = g.repo_root()
        self.assertIsNotNone(root)
        self.assertTrue(os.path.isabs(root))
        self.assertTrue(os.path.exists(root))

        # Not in git repo with flag='' - should return None
        g_no_repo = Git(GitOpt(), cwd="/tmp")
        result = g_no_repo.repo_root(flag="")
        self.assertIsNone(result)

        # Not in git repo with flag=['raise'] - should raise
        with self.assertRaises(CalledProcessError):
            g_no_repo.repo_root(flag=["raise"])

    def test_repo_is_repository(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Check with explicit path - should be True
        result = g.repo_is_repository(branch_test_worktree_p)
        self.assertTrue(result)

        # Check current directory (cwd) - should be True
        result = g.repo_is_repository()
        self.assertTrue(result)

        # Check non-repo directory - should be False
        result = g.repo_is_repository("/tmp")
        self.assertFalse(result)

        # Check non-existent path - should be False
        result = g.repo_is_repository("/nonexistent/path")
        self.assertFalse(result)


class TestGitHighlevel(BaseTest):
    def test_checkout(self):
        g = Git(GitOpt(), cwd=superp)
        g.checkout("master")
        self._fcontent("superman\n", superp, "imsuperman")

        self.assertRaises(CalledProcessError, g.checkout, "foo")

    def test_fetch(self):
        g = Git(GitOpt(), cwd=superp)

        g.fetch(wowgitp)
        hsh = g.cmdf("log", "-n1", "--format=%H", "FETCH_HEAD", flag=["oneline"])

        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", hsh)

    def test_fetch_url(self):
        g = Git(GitOpt(), cwd=superp)

        # Empty url validation
        with self.assertRaises(ValueError):
            g.fetch_url("", "refs/heads/master:refs/remotes/test/master")

        # Empty refspec validation
        with self.assertRaises(ValueError):
            g.fetch_url(wowgitp, "")

        # Successful fetch from URL
        g.fetch_url(wowgitp, "refs/heads/master:refs/remotes/test/master")
        hsh = g.cmdf("log", "-n1", "--format=%H", "refs/remotes/test/master", flag=["oneline"])
        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", hsh)

    def test_reset_to_commit(self):
        #  * 1315e30 (b2) add b2
        #  | * d1ec654 (base) add base
        #  |/
        #  * 3d7f424 (HEAD -> master, upstream/master, origin/master, dev) a

        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        g.cmdf("checkout", "b2")

        # build index
        fwrite(branch_test_worktree_p, "x", "x")
        g.cmdf("add", "x")
        fwrite(branch_test_worktree_p, "y", "y")
        g.cmdf("add", "y")

        # dirty worktree
        fwrite(branch_test_worktree_p, "x", "xx")

        # soft default to HEAD, nothing changed

        g.reset_to_commit("soft")

        out = g.cmdf("diff", "--name-only", "--relative", flag=["raise", "stdout"])
        self.assertEqual(
            [
                "x",
            ],
            out,
            "dirty worktree",
        )

        out = g.cmdf("diff", "--name-only", "--relative", "HEAD", flag=["raise", "stdout"])
        self.assertEqual(["x", "y"], out, "compare with HEAD")

        # soft to master

        g.reset_to_commit("soft", "master")

        out = g.cmdf("diff", "--name-only", "--relative", flag=["raise", "stdout"])
        self.assertEqual(
            [
                "x",
            ],
            out,
            "dirty worktree",
        )

        out = g.cmdf("diff", "--name-only", "--relative", "HEAD", flag=["raise", "stdout"])
        self.assertEqual(
            [
                "b2",
                "x",
                "y",
            ],
            out,
            "compare with HEAD",
        )

        # hard to master

        g.reset_to_commit("hard", "master")

        out = g.cmdf("diff", "--name-only", "--relative", "HEAD", flag=["raise", "stdout"])
        self.assertEqual([], out, "compare with HEAD")


class TestGitHead(BaseTest):
    def test_head_branch(self):
        # branch_test_git_p is a git-dir with one commit::
        # * 1d5ae3d (HEAD, origin/master, master) A  a

        # write a ".git" file to specify the git-dir for the containing
        # git-work-tree.
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)
        got = g.head_branch()
        self.assertEqual("master", got)

        # checkout to a commit pointing to no branch
        # It should return None
        g.checkout("origin/master")
        got = g.head_branch()
        self.assertIsNone(got)

        g.checkout("master")


class TestGitWorktree(BaseTest):
    def test_worktree_is_clean(self):
        # branch_test_git_p is a git-dir with one commit::
        # * 1d5ae3d (HEAD, origin/master, master) A  a

        # write a ".git" file to specify the git-dir for the containing
        # git-work-tree.
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        self.assertTrue(g.worktree_is_clean())

        fwrite(branch_test_worktree_p, "a", "foobarfoobar")
        self.assertFalse(g.worktree_is_clean())

    def test_worktree_staged_files(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # No staged files initially
        files = g.worktree_staged_files()
        self.assertEqual([], files)

        # Create and stage files
        fwrite(branch_test_worktree_p, "test1.txt", "content1")
        fwrite(branch_test_worktree_p, "test2.txt", "content2")
        g.add("test1.txt", "test2.txt")

        # Should return list of staged files
        files = g.worktree_staged_files()
        self.assertEqual(["test1.txt", "test2.txt"], sorted(files))

        # Commit and verify no staged files
        g.commit("test commit")
        files = g.worktree_staged_files()
        self.assertEqual([], files)


class TestGitBranch(BaseTest):
    # branch_test_git_p is a git-dir with one commit::
    # * 1d5ae3d (HEAD, origin/master, master) A  a

    # write a ".git" file to specify the git-dir for the containing
    # git-work-tree.

    def test_branch_default_remote(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)
        cases = [
            ("master", "origin"),
            ("dev", "upstream"),
            ("not_a_branch", None),
        ]

        for branch, remote in cases:
            got = g.branch_default_remote(branch)
            self.assertEqual(remote, got)

    def test_branch_default_upstream(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)
        cases = [
            ("master", "origin/master"),
            ("dev", "upstream/master"),
            ("not_a_branch", None),
        ]

        for branch, remote in cases:
            got = g.branch_default_upstream(branch)
            self.assertEqual(remote, got)

    def test_branch_set(self):
        g = Git(GitOpt(), cwd=superp)

        # parent of master
        parent = g.rev_of("master~")

        g.branch_set("master", "master~")

        self.assertEqual(parent, g.rev_of("master"))

    def test_branch_list(self):
        #  * 1315e30 (b2) add b2
        #  | * d1ec654 (base) add base
        #  |/
        #  * 3d7f424 (HEAD -> master, upstream/master, origin/master, dev) a

        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        got = g.branch_list()
        self.assertEqual(
            [
                "b2",
                "base",
                "dev",
                "master",
            ],
            got,
        )

    def test_branch_common_base(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)
        cases = [
            #  (['b2'], (['1315e30ec849dbbe67df3282139c0e0d3fdca606'], ['d1ec6549cffc507a2d41d5e363dcbd23754377c7'])),
            #  (['b2', 'base'], (['1315e30ec849dbbe67df3282139c0e0d3fdca606'], ['d1ec6549cffc507a2d41d5e363dcbd23754377c7'])),
            #  (['b2', 'master'], (['1315e30ec849dbbe67df3282139c0e0d3fdca606'], [])),
            (["b2", "base"], "3d7f4245f05db036309e9f74430d5479263637ad"),
            (["b2", "master"], "3d7f4245f05db036309e9f74430d5479263637ad"),
        ]

        for args, want in cases:
            got = g.branch_common_base(*args)
            self.assertEqual(want, got)

    def test_branch_divergency(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)
        cases = [
            (
                ["b2"],
                (
                    "3d7f4245f05db036309e9f74430d5479263637ad",
                    ["1315e30ec849dbbe67df3282139c0e0d3fdca606"],
                    ["d1ec6549cffc507a2d41d5e363dcbd23754377c7"],
                ),
            ),
            (
                ["b2", "base"],
                (
                    "3d7f4245f05db036309e9f74430d5479263637ad",
                    ["1315e30ec849dbbe67df3282139c0e0d3fdca606"],
                    ["d1ec6549cffc507a2d41d5e363dcbd23754377c7"],
                ),
            ),
            (
                ["b2", "master"],
                (
                    "3d7f4245f05db036309e9f74430d5479263637ad",
                    ["1315e30ec849dbbe67df3282139c0e0d3fdca606"],
                    [],
                ),
            ),
        ]

        for args, want in cases:
            got = g.branch_divergency(*args)
            self.assertEqual(want, got)

    def test_branch_rebase(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Empty upstream validation
        with self.assertRaises(ValueError):
            g.branch_rebase("")

        # Note: We can't test actual rebase without potentially creating conflicts
        # The method is tested through parameter validation

    def test_branch_merge_ff(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Empty string upstream validation (distinguish from None)
        with self.assertRaises(ValueError):
            g.branch_merge_ff("")

        # Note: We can't test actual merge without potentially creating conflicts
        # The method is tested through parameter validation


class TestGitRef(BaseTest):
    def test_ref_list(self):
        #  * 1315e30 (b2) add b2
        #  | * d1ec654 (base) add base
        #  |/
        #  * 3d7f424 (HEAD -> master, upstream/master, origin/master, dev) a

        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        got = g.ref_list()
        print(got)
        self.assertEqual(
            {
                "refs/heads/b2": "1315e30ec849dbbe67df3282139c0e0d3fdca606",
                "refs/heads/base": "d1ec6549cffc507a2d41d5e363dcbd23754377c7",
                "refs/heads/dev": "3d7f4245f05db036309e9f74430d5479263637ad",
                "refs/heads/master": "3d7f4245f05db036309e9f74430d5479263637ad",
                "refs/remotes/origin/master": "3d7f4245f05db036309e9f74430d5479263637ad",
                "refs/remotes/upstream/master": "3d7f4245f05db036309e9f74430d5479263637ad",
            },
            got,
        )

    def test_ref_delete(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Empty ref validation
        with self.assertRaises(ValueError):
            g.ref_delete("")

        # Create a test branch and delete it
        g.branch_set("test-delete-branch", "master")
        refs = g.ref_list()
        self.assertIn("refs/heads/test-delete-branch", refs)

        # Delete the branch reference
        g.ref_delete("refs/heads/test-delete-branch")
        refs = g.ref_list()
        self.assertNotIn("refs/heads/test-delete-branch", refs)

        # Deleting non-existent ref succeeds silently (git behavior)
        g.ref_delete("refs/heads/nonexistent", flag=["raise"])  # Should not raise


class TestGitRev(BaseTest):
    def test_rev_of(self):
        g = Git(GitOpt(), cwd=superp)
        t = g.rev_of("abc")
        self.assertIsNone(t)

        t = g.rev_of("master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.rev_of("refs/heads/master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.rev_of("c3954c897dfe40a5b99b7145820eeb227210265c")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)


class TestGitRemote(BaseTest):
    def test_remote_get(self):
        # TODO
        g = Git(GitOpt(), cwd=superp)
        t = g.remote_get("abc")
        self.assertIsNone(t)

        cmdx(origit, "remote", "add", "newremote", "newremote-url", cwd=superp)
        t = g.remote_get("newremote")
        self.assertEqual("newremote-url", t)

    def test_remote_add(self):
        # TODO
        g = Git(GitOpt(), cwd=superp)
        t = g.remote_get("abc")
        self.assertIsNone(t)

        g.remote_add("newremote", "newremote-url")
        t = g.remote_get("newremote")
        self.assertEqual("newremote-url", t)

    def test_remote_push(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Empty remote validation
        with self.assertRaises(ValueError):
            g.remote_push("", "master")

        # Empty branch validation
        with self.assertRaises(ValueError):
            g.remote_push("origin", "")

        # Note: We can't test actual push without a writable remote
        # The method is tested through parameter validation

    def test_remote_push_all(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Empty branch validation
        with self.assertRaises(ValueError):
            g.remote_push_all("")

        # Test with no remotes - should return empty dict
        # First remove any existing remotes
        remotes = g.cmdf("remote", flag=["raise", "stdout"])
        for remote in remotes:
            g.cmdf("remote", "remove", remote, flag=["raise"])

        results = g.remote_push_all("master")
        self.assertEqual({}, results)

        # Note: We can't test actual push without writable remotes
        # The method is tested through parameter validation and empty case


class TestGitBlob(BaseTest):
    def test_blob_new(self):
        fwrite(pjoin(superp, "newblob"), "newblob!!!")
        # TODO
        g = Git(GitOpt(), cwd=superp)
        blobhash = g.blob_new("newblob")

        content = cmd0(origit, "cat-file", "-p", blobhash, cwd=superp)
        self.assertEqual("newblob!!!", content)


class TestGitTree(BaseTest):
    def test_tree_commit(self):
        g = Git(GitOpt(), cwd=superp)

        # get the content of parent of master
        # Thus the changes looks like reverting the changes in master.
        tree = g.tree_of("master~")
        dd("tree:", tree)

        commit = g.tree_commit(tree, "test_tree_commit", [g.rev_of("master")])
        dd("commit:", commit)

        got = cmdout(origit, "log", commit, "-n2", "--stat", '--format="%s"', cwd=superp)
        dd(got)

        self.assertEqual(
            [
                '"test_tree_commit"',
                "",
                " imsuperman | 1 -",
                " 1 file changed, 1 deletion(-)",
                '"add super"',
                "",
                " imsuperman | 1 +",
                " 1 file changed, 1 insertion(+)",
            ],
            got,
        )

    def test_tree_items(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of("master")

        lines = g.tree_items(tree)
        self.assertEqual(
            [
                "100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\t.gift",
                "100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2\timsuperman",
            ],
            lines,
        )

        lines = g.tree_items(tree, with_size=True)
        self.assertEqual(
            [
                "100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c     163\t.gift",
                "100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2       9\timsuperman",
            ],
            lines,
        )

        lines = g.tree_items(tree, name_only=True)
        self.assertEqual([".gift", "imsuperman"], lines)

    def test_treeitem_parse(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of("master")
        lines = g.tree_items(tree, with_size=True)

        got = g.treeitem_parse(lines[0])
        self.assertEqual(
            {
                "fn": ".gift",
                "mode": "100644",
                "object": "15d2fff1101916d7212371fea0f3a82bda750f6c",
                "type": "blob",
                "size": "163",
            },
            got,
        )

    def test_tree_new(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of("master")
        lines = g.tree_items(tree)

        treeish = g.tree_new(lines)
        got = g.tree_items(treeish)

        self.assertEqual(
            [
                "100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\t.gift",
                "100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2\timsuperman",
            ],
            got,
        )

    def test_tree_new_replace(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of("master")
        lines = g.tree_items(tree)

        itm = g.treeitem_parse(lines[0])
        obj = itm["object"]

        treeish = g.tree_new_replace(lines, "foo", obj, mode="100755")
        got = g.tree_items(treeish)

        self.assertEqual(
            [
                "100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\t.gift",
                "100755 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo",
                "100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2\timsuperman",
            ],
            got,
        )

    def test_add_tree(self):
        # TODO opt
        g = Git(GitOpt(), cwd=superp)

        roottreeish = g.tree_of("HEAD")

        dd(
            cmdx(
                origit,
                "ls-tree",
                "87486e2d4543eb0dd99c1064cc87abdf399cde9f",
                cwd=superp,
            )
        )
        self.assertEqual("87486e2d4543eb0dd99c1064cc87abdf399cde9f", roottreeish)

        # shallow add

        newtree = g.tree_add_obj(roottreeish, "nested", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual(
            [
                ".gift",
                "imsuperman",
                "nested/.gift",
                "nested/imsuperman",
            ],
            files,
        )

        # add nested

        newtree = g.tree_add_obj(newtree, "a/b/c/d", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual(
            [
                ".gift",
                "a/b/c/d/.gift",
                "a/b/c/d/imsuperman",
                "imsuperman",
                "nested/.gift",
                "nested/imsuperman",
            ],
            files,
        )

        # replace nested

        newtree = g.tree_add_obj(newtree, "a/b/c", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual(
            [
                ".gift",
                "a/b/c/.gift",
                "a/b/c/imsuperman",
                "imsuperman",
                "nested/.gift",
                "nested/imsuperman",
            ],
            files,
        )

        # replace a blob with tree

        newtree = g.tree_add_obj(newtree, "a/b/c/imsuperman", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual(
            [
                ".gift",
                "a/b/c/.gift",
                "a/b/c/imsuperman/.gift",
                "a/b/c/imsuperman/imsuperman",
                "imsuperman",
                "nested/.gift",
                "nested/imsuperman",
            ],
            files,
        )

        # replace a blob in mid of path with tree

        newtree = g.tree_add_obj(newtree, "nested/imsuperman/b/c", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual(
            [
                ".gift",
                "a/b/c/.gift",
                "a/b/c/imsuperman/.gift",
                "a/b/c/imsuperman/imsuperman",
                "imsuperman",
                "nested/.gift",
                "nested/imsuperman/b/c/.gift",
                "nested/imsuperman/b/c/imsuperman",
            ],
            files,
        )


class TestGitTreeItem(BaseTest):
    def test_treeitem_new(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of("master")
        lines = g.tree_items(tree, with_size=True)
        itm = g.treeitem_parse(lines[0])
        obj = itm["object"]

        got = g.treeitem_new("foo", obj)
        self.assertEqual("100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo", got)

        got = g.treeitem_new("foo", obj, mode="100755")
        self.assertEqual("100755 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo", got)


class TestGitAdd(BaseTest):
    def test_add(self):
        # Test that add requires files when update=False
        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        with self.assertRaises(ValueError):
            g.add()

        # Create test files
        fwrite(branch_test_worktree_p, "test1.txt", "test content 1")
        fwrite(branch_test_worktree_p, "test2.txt", "test content 2")

        # Test adding specific files
        g.add("test1.txt")
        out = g.cmdf("status", "--short", flag=["raise", "stdout"])
        self.assertIn("A  test1.txt", "\n".join(out))

        # Test adding multiple files
        g.add("test2.txt", "test1.txt")
        out = g.cmdf("status", "--short", flag=["raise", "stdout"])
        self.assertIn("A  test2.txt", "\n".join(out))

        # Commit to have tracked files for update test
        g.cmdf("commit", "-m", "Add test files", flag=["raise"])

        # Modify files
        fwrite(branch_test_worktree_p, "test1.txt", "modified content 1")
        fwrite(branch_test_worktree_p, "test2.txt", "modified content 2")

        # Test update=True (should work without files)
        g.add(update=True)
        out = g.cmdf("status", "--short", flag=["raise", "stdout"])
        self.assertIn("M  test1.txt", "\n".join(out))
        self.assertIn("M  test2.txt", "\n".join(out))

    def test_commit(self):
        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Create and add test file
        fwrite(branch_test_worktree_p, "commit_test.txt", "test content")
        g.add("commit_test.txt")

        # Test commit with message
        commit_hash = g.commit("Add commit test file")

        # Verify commit was created
        self.assertTrue(commit_hash)
        self.assertEqual(len(commit_hash), 40)  # SHA-1 hash length

        # Verify commit message
        out = g.cmdf("log", "-1", "--pretty=format:%s", flag=["raise", "stdout"])
        self.assertEqual(["Add commit test file"], out)

        # Verify the commit hash matches HEAD
        head_hash = g.cmdf("rev-parse", "HEAD", flag=["raise", "none", "oneline"])
        self.assertEqual(commit_hash, head_hash)


class TestGitLog(BaseTest):
    def test_log_date(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Success case - get date from HEAD
        date = g.log_date("HEAD")
        self.assertIsNotNone(date)
        self.assertIsInstance(date, str)

        # Success case - get date from master
        date = g.log_date("master")
        self.assertIsNotNone(date)

        # Custom format - ISO 8601
        date = g.log_date("HEAD", format="%ai")
        self.assertIsNotNone(date)
        self.assertIn("-", date)  # ISO format contains dashes

        # Not found with flag='' - should return None
        result = g.log_date("nonexistent", flag="")
        self.assertIsNone(result)

        # Not found with flag='x' - should raise
        with self.assertRaises(CalledProcessError):
            g.log_date("nonexistent", flag=["raise"])

        # Empty ref validation
        with self.assertRaises(ValueError):
            g.log_date("")

    def test_log_grep(self):
        fwrite(branch_test_worktree_p, ".git", "gitdir: ../branch_test_git")

        g = Git(GitOpt(), cwd=branch_test_worktree_p)

        # Create commits with specific messages for testing
        fwrite(branch_test_worktree_p, "file1.txt", "content1")
        g.add("file1.txt")
        g.commit("fix bug in parser")

        fwrite(branch_test_worktree_p, "file2.txt", "content2")
        g.add("file2.txt")
        g.commit("add new feature")

        # Search for pattern in commit messages
        commits = g.log_grep("fix")
        self.assertEqual(1, len(commits))

        commits = g.log_grep("add")
        self.assertEqual(1, len(commits))

        # Search with max_count
        commits = g.log_grep("add", max_count=1)
        self.assertEqual(1, len(commits))

        # Search for non-existent pattern - should return empty list
        commits = g.log_grep("nonexistent")
        self.assertEqual([], commits)

        # Empty pattern validation
        with self.assertRaises(ValueError):
            g.log_grep("")

        # Invalid grep_type validation
        with self.assertRaises(ValueError):
            g.log_grep("test", grep_type="invalid")

        # Invalid max_count validation
        with self.assertRaises(ValueError):
            g.log_grep("test", max_count=0)

        with self.assertRaises(ValueError):
            g.log_grep("test", max_count=-1)


class TestGitOut(BaseTest):
    def test_out(self):
        script = r"""import k3git; k3git.Git(k3git.GitOpt(), ctxmsg="foo").out(1, "bar", "wow")"""

        got = cmdf("python", "-c", script, flag=["raise", "oneline"])
        self.assertEqual("foo: bar wow", got)


def _clean_case():
    force_remove(pjoin(this_base, "testdata", "super", ".git"))
    cmdx(origit, "reset", "testdata", cwd=this_base)
    cmdx(origit, "checkout", "testdata", cwd=this_base)
    cmdx(origit, "clean", "-dxf", cwd=this_base)


def force_remove(fn):
    try:
        shutil.rmtree(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
