UV ?= uv
RUN = $(UV) run
REFERENCE_ARGS ?= --max-episodes 10
TRANSLATE_URL ?= http://localhost:5000

.DEFAULT_GOAL := help

.PHONY: help sync lock-check lint fix format format-check typecheck test quality check story build-site reference reference-translate deploy clean

help:
	@echo "story_gen targets:"
	@echo "  make sync                 - install/update dependencies with uv"
	@echo "  make lock-check           - verify uv.lock matches pyproject constraints"
	@echo "  make lint                 - run ruff checks"
	@echo "  make fix                  - auto-fix lint issues and format code"
	@echo "  make format               - format code with ruff"
	@echo "  make format-check         - verify formatting without changing files"
	@echo "  make typecheck            - run mypy"
	@echo "  make test                 - run pytest"
	@echo "  make quality              - lock-check + lint + format-check + typecheck + tests"
	@echo "  make check                - run lint + typecheck + tests"
	@echo "  make story                - run the story_gen CLI"
	@echo "  make build-site           - build static story site"
	@echo "  make reference            - run reference pipeline (override REFERENCE_ARGS)"
	@echo "  make reference-translate  - run reference pipeline with LibreTranslate"
	@echo "  make deploy               - run checks, build site, and push main"
	@echo "  make clean                - remove local caches and generated site/"

sync:
	$(UV) sync --all-groups

lock-check:
	$(UV) lock --check

lint:
	$(RUN) ruff check .

fix:
	$(RUN) ruff check . --fix
	$(RUN) ruff format .

format:
	$(RUN) ruff format .

format-check:
	$(RUN) ruff format --check .

typecheck:
	$(RUN) mypy

test:
	$(RUN) pytest

quality: lock-check lint format-check typecheck test

check: quality

story:
	$(RUN) story-gen

build-site:
	$(RUN) python scripts/build_story_site.py

reference:
	$(RUN) story-reference $(REFERENCE_ARGS)

reference-translate:
	$(RUN) story-reference --translate-provider libretranslate --libretranslate-url $(TRANSLATE_URL) $(REFERENCE_ARGS)

deploy: quality build-site
	git push origin main

clean:
	$(RUN) python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.mypy_cache', '.ruff_cache', 'site']]"
