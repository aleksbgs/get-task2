TERRAFORM ?= terraform
PYTHON ?= python3
RUFF ?= uvx ruff==0.16.9
TF = $(TERRAFORM) -chdir=terraform

.PHONY: init build format check test package

init:
	$(TF) init -backend=false -lockfile=readonly

build:
	$(PYTHON) scripts/build.py

format:
	$(TF) fmt -recursive
	$(RUFF) format src scripts tests

check:
	$(TF) fmt -check -recursive
	$(TF) validate
	$(RUFF) check src scripts tests
	$(RUFF) format --check src scripts tests
	$(MAKE) test

test:
	$(TF) test
	uv run --no-project --with-requirements requirements.txt python -m unittest discover -s tests -v

package:
	$(PYTHON) scripts/package.py
