PYTHON_FILES := ci $(shell find . -type f -iname '*.py')
SHELL_FILES := $(shell find . -type f -iname '*.sh')
YAML_FILES := .

all:

fix: fix-python

fix-python:
	black --line-length 79 $(PYTHON_FILES)
	isort $(PYTHON_FILES)

test: test-python test-shell test-yaml

test-python:
	black --check --line-length 79 --quiet $(PYTHON_FILES)
	isort --check-only $(PYTHON_FILES)
	pycodestyle --ignore=E203 $(PYTHON_FILES)
	pylint3 $(PYTHON_FILES)

test-shell:
	shellcheck $(SHELL_FILES)

test-yaml:
	yamllint --strict $(YAML_FILES)

.PHONY: all fix fix-python test test-python test-shell test-yaml
