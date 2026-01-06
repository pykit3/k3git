# k3git

[![Action-CI](https://github.com/pykit3/k3git/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3git/actions/workflows/python-package.yml)
[![Documentation Status](https://readthedocs.org/projects/k3git/badge/?version=stable)](https://k3git.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3git)](https://pypi.org/project/k3git)

A wrapper for git command-line operations.

k3git is a component of [pykit3](https://github.com/pykit3) project: a python3 toolkit set.

## Installation

```bash
pip install k3git
```

## Quick Start

### Parse git command arguments

```python
from k3git import GitOpt

opt = GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin'])
print(opt.cmds)      # ['fetch', 'origin']
print(opt.to_args()) # ['--git-dir=/foo']
```

### Work with git repositories

```python
from k3git import Git

git = Git('/path/to/repo')
git.commit('commit message')
```

### Parse git URLs

```python
from k3git import GitUrl

url = GitUrl.parse('git@github.com:pykit3/k3git.git')
print(url.host)  # github.com
print(url.path)  # pykit3/k3git
```

## API Reference

::: k3git.Git

::: k3git.GitOpt

::: k3git.GitUrl

## License

The MIT License (MIT) - Copyright (c) 2015 Zhang Yanpo (张炎泼)
