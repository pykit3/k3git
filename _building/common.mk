all: test lint readme doc

.PHONY: test lint
sudo_test:
	sudo env "PATH=$$PATH" UT_DEBUG=0 pytest -v

test:
	env UT_DEBUG=0 pytest -v

doc:
	mkdocs build

lint:
	# ruff format: fast Python code formatter (Black-compatible)
	uvx ruff format .
	# ruff check: fast Python linter with auto-fixes
	uvx ruff check --fix .

static_check:
	# mypy: static type checker for Python
	uvx mypy . --ignore-missing-imports

readme:
	pk3 readme

release:
	pk3 tag

publish:
	pk3 publish

install:
	pip install -e .
