#!/usr/bin/env python
# coding: utf-8

import re

#  https://stackoverflow.com/questions/31801271/what-are-the-supported-git-url-formats
#  I found the list below. It is not complete since
#  https://<token>:x-oauth-basic@host.xz/path/to/repo.git is not there.
#
#  Secure Shell Transport Protocol
#  ssh://user@host.xz:port/path/to/repo.git/
#  ssh://user@host.xz/path/to/repo.git/
#  ssh://host.xz:port/path/to/repo.git/
#  ssh://host.xz/path/to/repo.git/
#  ssh://user@host.xz/path/to/repo.git/
#  ssh://host.xz/path/to/repo.git/
#  ssh://user@host.xz/~user/path/to/repo.git/
#  ssh://host.xz/~user/path/to/repo.git/
#  ssh://user@host.xz/~/path/to/repo.git
#  ssh://host.xz/~/path/to/repo.git
#  user@host.xz:/path/to/repo.git/
#  host.xz:/path/to/repo.git/
#  user@host.xz:~user/path/to/repo.git/
#  host.xz:~user/path/to/repo.git/
#  user@host.xz:path/to/repo.git
#  host.xz:path/to/repo.git
#  rsync://host.xz/path/to/repo.git/
#
#  Git Transport Protocol
#  git://host.xz/path/to/repo.git/
#  git://host.xz/~user/path/to/repo.git/
#
#  HTTP/S Transport Protocol
#  http://host.xz/path/to/repo.git/
#  https://host.xz/path/to/repo.git/

#  Secure Shell Transport Protocol

#  ssh://(?P<user>.*?)@(?P<host>.*?):(?P<port>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?):(?P<port>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/~user/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<user>.*?)@(?P<host>.*?)/~/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  ssh://(?P<host>.*?)/~/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):~user/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<user>.*?)@(?P<host>.*?):(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  (?P<host>.*?):(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  rsync://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$

#  Git Transport Protocol

#  git://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  git://(?P<host>.*?)/~(?P<user>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$

#  HTTP/S Transport Protocol

#  http://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$
#  https://(?P<host>.*?)/(?P<user>.*?)/(?P<repo>.*?)(\.git)?(/)?(?P<branch>@.*?)?$


rule_groups = [{
    "defaults": {
        "host": "github.com",
    },
    "provider": "github.com",
    "fmt": {
        "ssh": 'git@{host}:{user}/{repo}.git',
        "https": 'https://{host}/{user}/{repo}.git',
        "https_token": 'https://{committer}:{token}@{host}/{user}/{repo}.git',
    },
    "patterns": [
        # git@github.com:openacid/slim.git
        r'git@github.com:(?P<user>.*?)/(?P<repo>.*?)(\.git)?(?P<branch>@.*?)?$',
        # ssh://git@github.com/openacid/openacid.github.io
        r'ssh://git@github.com/(?P<user>.*?)/(?P<repo>.*?)(?P<branch>@.*?)?$',
        # https://committer:token@github.com/openacid/openacid.github.io.git
        r'https://(?P<committer>.*?):(?P<token>.*?)@github.com/(?P<user>.*?)/(?P<repo>.*?)\.git(?P<branch>@.*?)?$',
        # http://github.com/openacid/openacid.github.io.git
        r'http://github.com/(?P<user>.*?)/(?P<repo>.*?)\.git(?P<branch>@.*?)?$',
        # https://github.com/openacid/openacid.github.io.git
        r'https://github.com/(?P<user>.*?)/(?P<repo>.*?)\.git(?P<branch>@.*?)?$',
    ],
},
]


class GitUrl(object):
    """
    GitUrl parse and format git urls
    """

    def __init__(self, fields, rule_group):
        self.fields = fields
        self.rule_group = rule_group

    def fmt(self, scheme):
        """
        format git url to scheme ssh or https

        Args:

           scheme(str): specifies the output url format:

                        - ``"ssh": 'git@{host}:{user}/{repo}.git'``,

                        - ``"https": 'https://{host}/{user}/{repo}.git'``,

        Returns:
            str: the formatted url
        """
        if scheme == 'https':
            if 'token' in self.fields:
                fmt = self.rule_group['fmt']['https_token']
            else:
                fmt = self.rule_group['fmt']['https']
        elif scheme == 'ssh':
            fmt = self.rule_group['fmt']['ssh']
        else:
            raise ValueError("invalid scheme: "+scheme)

        return fmt.format(**self.fields)

    @classmethod
    def parse(cls, url):
        """
        Parse plain text git url and return an instance of GitUrl.

        Args:

            url(str): git url in string in one form of:

                    - ``git@github.com:openacid/slim.git``
                    - ``ssh://git@github.com/openacid/openacid.github.io``
                    - ``https://committer:token@github.com/openacid/openacid.github.io.git``
                    - ``http://github.com/openacid/openacid.github.io.git``
                    - ``https://github.com/openacid/openacid.github.io.git``

        Returns:
            GitUrl
        """

        for g in rule_groups:
            for p in g['patterns']:
                match = re.match(p, url)
                if match:
                    d = match.groupdict()
                    d.update(g['defaults'])

                    return cls(d, g)

        raise ValueError(
            'unknown url: {url};'.format(
                url=url,
                )
        )
