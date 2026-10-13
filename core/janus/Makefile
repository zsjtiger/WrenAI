# Package and publish the `janusai` distribution (this directory) to PyPI.
#
#   make build                          build sdist + wheel into dist/
#   make check                          build, then validate with twine
#   make publish-test                   upload to TestPyPI
#   CONFIRM=yes make publish            upload to PyPI (irreversible)
#
# Requires uv (https://docs.astral.sh/uv/) and twine (pip install twine).
# Credentials come from TWINE_USERNAME/TWINE_PASSWORD or ~/.pypirc.

UV ?= uv
TWINE ?= twine
PIP ?= python3 -m pip
DIST := dist
VERSION := $(shell sed -nE 's/^version\s*=\s*"([^"]+)".*/\1/p' pyproject.toml | head -n1)
# Runtime dependency that must be on the index before janusai can be installed.
ENGINE_DEP := janus-core-py

.PHONY: help version clean build check check-engine-dep publish-test publish

help:
	@echo "janusai $(VERSION)"
	@echo "  make build          build sdist + wheel into $(DIST)/"
	@echo "  make check          build and run twine check"
	@echo "  make publish-test   upload to TestPyPI"
	@echo "  CONFIRM=yes make publish   upload to PyPI"

version:
	@echo $(VERSION)

clean:
	rm -rf $(DIST) build *.egg-info

build: clean
	@test -n "$(VERSION)" || { echo "error: could not read version from pyproject.toml"; exit 1; }
	$(UV) build
	@ls -lh $(DIST)

check: build
	$(TWINE) check $(DIST)/*

check-engine-dep:
	@$(PIP) index versions $(ENGINE_DEP) >/dev/null 2>&1 || { \
		echo "error: $(ENGINE_DEP) is not on the package index."; \
		echo "       janusai depends on it, so a published janusai would not install."; \
		echo "       Publish $(ENGINE_DEP) first, then re-run."; \
		exit 1; }

publish-test: check
	$(TWINE) upload --repository testpypi $(DIST)/*

publish: check check-engine-dep
	@test "$(CONFIRM)" = "yes" || { \
		echo "Refusing to publish to PyPI. Re-run with CONFIRM=yes to upload janusai $(VERSION)."; \
		exit 1; }
	$(TWINE) upload --repository pypi $(DIST)/*
