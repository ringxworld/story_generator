UV ?= uv
RUN = $(UV) run
REFERENCE_ARGS ?= --max-episodes 10
TRANSLATE_URL ?= http://localhost:5000
CPP_BUILD_DIR ?= build/cpp
CPP_CONFIG ?= Release

.DEFAULT_GOAL := help

.PHONY: help sync hooks-install hooks-run lock-check lint fix format format-check typecheck test quality check story build-site reference reference-translate cpp-configure cpp-build cpp-test cpp-demo cpp-format cpp-format-check cpp-cppcheck deploy clean

help:
	@echo "story_gen targets:"
	@echo "  make sync                 - install/update dependencies with uv"
	@echo "  make hooks-install        - install git pre-commit and pre-push hooks"
	@echo "  make hooks-run            - run pre-commit on all files"
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
	@echo "  make cpp-configure        - configure C++ tooling with CMake"
	@echo "  make cpp-build            - build C++ tools"
	@echo "  make cpp-test             - run C++ tests (ctest)"
	@echo "  make cpp-demo             - run chapter_metrics demo output"
	@echo "  make cpp-format           - format C++ files with clang-format"
	@echo "  make cpp-format-check     - verify C++ formatting"
	@echo "  make cpp-cppcheck         - run cppcheck on C++ sources"
	@echo "  make deploy               - run checks, build site, and push main"
	@echo "  make clean                - remove local caches and generated site/"

sync:
	$(UV) sync --all-groups

hooks-install:
	$(RUN) pre-commit install --hook-type pre-commit --hook-type pre-push

hooks-run:
	$(RUN) pre-commit run --all-files

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

cpp-configure:
	cmake -S . -B $(CPP_BUILD_DIR)

cpp-build: cpp-configure
	cmake --build $(CPP_BUILD_DIR) --config $(CPP_CONFIG)

cpp-test: cpp-build
	ctest --test-dir $(CPP_BUILD_DIR) -C $(CPP_CONFIG) --output-on-failure

cpp-demo: cpp-build
	ctest --test-dir $(CPP_BUILD_DIR) -C $(CPP_CONFIG) -R chapter_metrics_demo --output-on-failure

cpp-format:
	clang-format -i cpp/*.cpp

cpp-format-check:
	clang-format --dry-run --Werror cpp/*.cpp

cpp-cppcheck:
	cppcheck --enable=warning,style,performance,portability --error-exitcode=2 cpp

deploy: quality build-site
	git push origin main

clean:
	$(RUN) python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.mypy_cache', '.ruff_cache', 'site']]"
