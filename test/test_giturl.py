import os
import unittest

import k3ut
from k3git import GitUrl

dd = k3ut.dd

this_base = os.path.dirname(__file__)


class TestGitUrl(unittest.TestCase):

    def test_giturl_parse(self):
        cases = (
                ('git@github.com:openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # with branch
                ('git@github.com:openacid/slim.git@my_branch',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # with scheme ssh://
                ('ssh://git@github.com/openacid/slim',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                # https with committer:token for auth
                ('https://committer:token@github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://committer:token@github.com/openacid/slim.git',
                ),
                ('http://github.com/openacid/slim.git',
                 'git@github.com:openacid/slim.git',
                 'https://github.com/openacid/slim.git',
                ),
                ('https://github.com/openacid/slim.git',
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
