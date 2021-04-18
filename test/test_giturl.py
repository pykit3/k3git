import os
import unittest

import k3ut
from k3git import GitUrl

dd = k3ut.dd

this_base = os.path.dirname(__file__)


class TestGitUrl(unittest.TestCase):

    def test_giturl_parse(self):
        cases = (
                #  simplified form
                ('github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),

                #  without .git
                ('git@github.com:openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # .git
                ('git@github.com:openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # with .git and trailing slash
                ('git@github.com:openacid/slim.git/',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),

                # with branch
                ('git@github.com:openacid/slim.git@my_branch',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),

                # ssh://

                # with scheme ssh://
                ('ssh://git@github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # with scheme ssh://  and .git
                ('ssh://git@github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # with scheme ssh://  and .git and trailing slash
                ('ssh://git@github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),

                # https:// with token

                # https with committer:token for auth
                ('https://committer:token@github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://committer:token@github.com/openacid/slim.git',
                ),

                # http

                ('http://github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                ('http://github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                ('http://github.com/openacid/slim.git/',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),

                # https

                ('https://github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                ('https://github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                ('https://github.com/openacid/slim.git/',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
        )

        for inp, wantssh, wanthttps in cases:

            dd(inp)
            dd(wantssh)
            dd(wanthttps)

            got = GitUrl.parse(inp)
            self.assertEqual(wantssh, got.fmt('ssh'))
            self.assertEqual(wanthttps, got.fmt('https'))

            #  self.assertEqual({'branch': None, 'host': 'github.com', 'repo': 'slim', 'user': 'openacid'},  got.dic)

    def test_giturl_parse_token_from_env(self):
        cases = (

                # https

                ('https://github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://foo:bar@github.com/openacid/slim.git',
                ),

                # env does not override explicit param

                ('https://a:b@github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://a:b@github.com/openacid/slim.git',
                ),
        )

        for inp, wantssh, wanthttps in cases:

            dd(inp)
            dd(wantssh)
            dd(wanthttps)


            os.environ["GITHUB_USERNAME"] = "foo"
            os.environ["GITHUB_TOKEN"] = "bar"
            got = GitUrl.parse(inp)

            self.assertEqual(wantssh, got.fmt('ssh'))
            self.assertEqual(wanthttps, got.fmt('https'))

            del os.environ["GITHUB_USERNAME"]
            del os.environ["GITHUB_TOKEN"]
