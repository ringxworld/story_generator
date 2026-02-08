UV ?= uv
RUN = $(UV) run
REFERENCE_ARGS ?= --max-episodes 10
TRANSLATE_URL ?= http://localhost:5000
STORY_SERIES_CODE ?= n2866cb
VIDEO_URL ?=
VIDEO_ARGS ?=
CPP_BUILD_DIR ?= build/cpp
CPP_CONFIG ?= Release

.DEFAULT_GOAL := help

.PHONY: help sync hooks-install hooks-run lock-check import-check lint fix format format-check typecheck test e2e coverage quality frontend-quality native-quality check story build-site docs-serve story-page reference reference-translate collect-story video-story api blueprint features dev-stack dev-stack-hot stack-up stack-up-hot docker-build docker-up docker-down docker-logs docker-ci web-install web-dev web-hot web-typecheck web-test web-coverage web-build cpp-configure cpp-build cpp-test cpp-demo cpp-format cpp-format-check cpp-cppcheck deploy clean

help:
	@echo "story_gen targets:"
	@echo "  make sync                 - install/update dependencies with uv"
	@echo "  make hooks-install        - install git pre-commit and pre-push hooks"
	@echo "  make hooks-run            - run pre-commit on all files"
	@echo "  make lock-check           - verify uv.lock matches pyproject constraints"
	@echo "  make import-check         - enforce Python import layer boundaries"
	@echo "  make lint                 - run ruff checks"
	@echo "  make fix                  - auto-fix lint issues and format code"
	@echo "  make format               - format code with ruff"
	@echo "  make format-check         - verify formatting without changing files"
	@echo "  make typecheck            - run mypy"
	@echo "  make test                 - run pytest with coverage gate"
	@echo "  make e2e                  - run process-level end-to-end API tests"
	@echo "  make coverage             - run pytest with coverage gate"
	@echo "  make quality              - lock-check + lint + format-check + typecheck + tests"
	@echo "  make frontend-quality     - frontend typecheck + coverage + build"
	@echo "  make native-quality       - native format check + cppcheck"
	@echo "  make check                - full local gate (python + frontend + native)"
	@echo "  make story                - run the story_gen CLI"
	@echo "  make build-site           - build MkDocs pages site"
	@echo "  make docs-serve           - serve MkDocs locally"
	@echo "  make story-page           - build standalone story HTML page"
	@echo "  make reference            - run reference pipeline (override REFERENCE_ARGS)"
	@echo "  make reference-translate  - run reference pipeline with LibreTranslate"
	@echo "  make collect-story        - collect full text for STORY_SERIES_CODE"
	@echo "  make video-story          - download VIDEO_URL audio and optional transcript"
	@echo "  make api                  - run local API stub server"
	@echo "  make blueprint            - validate/normalize a blueprint JSON file"
	@echo "  make features             - extract persisted chapter features for one story"
	@echo "  make dev-stack            - run API + web dev servers together"
	@echo "  make dev-stack-hot        - run API + hot-edit web server together (web on :5174)"
	@echo "  make stack-up             - bootstrap deps, build web bundle, then run dev stack"
	@echo "  make stack-up-hot         - bootstrap deps, build web bundle, then run hot-edit stack"
	@echo "  make docker-build         - build local Docker images (API + web)"
	@echo "  make docker-up            - launch API + web via docker compose"
	@echo "  make docker-down          - stop docker compose services"
	@echo "  make docker-logs          - tail docker compose logs"
	@echo "  make docker-ci            - run full project checks in CI Docker image"
	@echo "  make web-install          - install frontend dependencies"
	@echo "  make web-dev              - run React+TS frontend dev server"
	@echo "  make web-hot              - run dedicated hot-edit frontend server on :5174"
	@echo "  make web-typecheck        - run frontend TypeScript checks"
	@echo "  make web-test             - run frontend tests"
	@echo "  make web-coverage         - run frontend tests with coverage thresholds"
	@echo "  make web-build            - build frontend production bundle"
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
	$(RUN) pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push

hooks-run:
	$(RUN) pre-commit run --all-files

lock-check:
	$(UV) lock --check

import-check:
	$(RUN) python tools/check_imports.py

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

e2e:
	$(RUN) pytest tests/test_e2e_stack.py

coverage: test

quality: lock-check import-check lint format-check typecheck test

frontend-quality: web-typecheck web-coverage web-build

native-quality: cpp-format-check cpp-cppcheck

check: quality frontend-quality native-quality

story:
	$(RUN) story-gen

build-site:
	$(RUN) mkdocs build --strict

docs-serve:
	$(RUN) mkdocs serve

story-page:
	$(RUN) python -m story_gen.site_builder

reference:
	$(RUN) story-reference $(REFERENCE_ARGS)

reference-translate:
	$(RUN) story-reference --translate-provider libretranslate --libretranslate-url $(TRANSLATE_URL) $(REFERENCE_ARGS)

collect-story:
	$(RUN) story-collect --series-code $(STORY_SERIES_CODE)

video-story:
	$(RUN) story-video --url "$(VIDEO_URL)" $(VIDEO_ARGS)

api:
	$(RUN) story-api

blueprint:
	$(RUN) story-blueprint --input work/story_blueprint.json

features:
	$(RUN) story-features --story-id $$STORY_ID --owner-id $$OWNER_ID

dev-stack:
	$(RUN) python tools/dev_stack.py

dev-stack-hot:
	$(RUN) python tools/dev_stack.py --web-port 5174

stack-up: sync web-install web-build
	$(RUN) python tools/dev_stack.py

stack-up-hot: sync web-install web-build
	$(RUN) python tools/dev_stack.py --web-port 5174

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down --remove-orphans

docker-logs:
	docker compose logs -f

docker-ci:
	docker build -f docker/ci.Dockerfile -t story-gen-ci .
	docker run --rm story-gen-ci

web-install:
	npm install --prefix web

web-dev:
	npm run --prefix web dev

web-hot:
	npm run --prefix web dev:hot

web-typecheck:
	npm run --prefix web typecheck

web-test:
	npm run --prefix web test

web-coverage:
	npm run --prefix web test:coverage

web-build:
	npm run --prefix web build

cpp-configure:
	cmake -S . -B $(CPP_BUILD_DIR)

cpp-build: cpp-configure
	cmake --build $(CPP_BUILD_DIR) --config $(CPP_CONFIG)

cpp-test: cpp-build
	ctest --test-dir $(CPP_BUILD_DIR) -C $(CPP_CONFIG) --output-on-failure

cpp-demo: cpp-build
	ctest --test-dir $(CPP_BUILD_DIR) -C $(CPP_CONFIG) -R chapter_metrics_demo --output-on-failure

cpp-format:
	$(RUN) clang-format -i cpp/*.cpp

cpp-format-check:
	$(RUN) clang-format --dry-run --Werror cpp/*.cpp

cpp-cppcheck:
	cppcheck --enable=warning,style,performance,portability --error-exitcode=2 cpp

deploy: quality build-site
	git push origin main

clean:
	$(RUN) python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.mypy_cache', '.ruff_cache', 'site']]"
