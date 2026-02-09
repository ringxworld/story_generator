import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_makefile_contains_quality_and_native_targets() -> None:
    makefile = _read("Makefile")
    assert "hooks-install:" in makefile
    assert "hooks-run:" in makefile
    assert "quality:" in makefile
    assert "deploy: quality build-site" in makefile
    assert "cpp-configure:" in makefile
    assert "cpp-build:" in makefile
    assert "cpp-test:" in makefile
    assert "cpp-demo:" in makefile
    assert "cpp-format:" in makefile
    assert "cpp-format-check:" in makefile
    assert "cpp-cppcheck:" in makefile
    assert "wiki-sync:" in makefile
    assert "wiki-sync-push:" in makefile
    assert "contracts-export:" in makefile
    assert "pr-open:" in makefile
    assert "pr-checks:" in makefile
    assert "pr-merge:" in makefile
    assert "pr-auto:" in makefile
    assert "clean:" in makefile
    assert "clean-deep:" in makefile
    assert "collect-story:" in makefile
    assert "video-story:" in makefile
    assert "features:" in makefile
    assert "dev-stack-hot:" in makefile
    assert "stack-up-hot:" in makefile
    assert "web-hot:" in makefile
    assert "brand-icons:" in makefile
    assert "docker-build:" in makefile
    assert "docker-up:" in makefile
    assert "docker-down:" in makefile
    assert "docker-logs:" in makefile
    assert "docker-ci:" in makefile
    assert "e2e:" in makefile
    assert "pytest tests/test_e2e_stack.py" in makefile
    assert "import-check:" in makefile
    assert "quality: lock-check import-check" in makefile
    assert "frontend-quality:" in makefile
    assert "native-quality:" in makefile
    assert "web-coverage:" in makefile


def test_ci_workflow_includes_code_quality_steps() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "- develop" in workflow
    assert "- main" in workflow
    assert "uv sync --group dev" in workflow
    assert "Pre-commit hooks (all files)" in workflow
    assert "uv lock --check" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run ruff format --check ." in workflow
    assert "uv run mypy" in workflow
    assert "uv run pytest" in workflow
    assert "uv run mkdocs build --strict" in workflow
    assert "uv run python tools/check_imports.py" in workflow
    assert "Configure CMake" in workflow
    assert "Run native tests" in workflow
    assert "Install native quality tools" in workflow
    assert "C++ format check" in workflow
    assert "Cppcheck" in workflow
    assert "Frontend typecheck" in workflow
    assert "Frontend tests (coverage gate)" in workflow
    assert "npm run --prefix web test:coverage" in workflow
    assert "Frontend build" in workflow
    assert "Build docs site artifact" in workflow
    assert "Build offline studio artifact" in workflow
    assert "VITE_OFFLINE_DEMO" in workflow
    assert "Build API Docker image" in workflow
    assert "Build web Docker image" in workflow
    assert "Docker compose stack smoke test" in workflow
    assert "Build CI Docker image" in workflow
    assert "Run full checks in CI Docker image" in workflow


def test_deploy_workflow_requires_ci_success() -> None:
    workflow = _read(".github/workflows/deploy-pages.yml")
    assert "workflow_run:" in workflow
    assert "workflows:" in workflow
    assert "- CI" in workflow
    assert "conclusion == 'success'" in workflow
    assert "head_branch == 'develop'" in workflow
    assert "head_branch == 'main'" in workflow
    assert "Setup Node" in workflow
    assert "Build product demo snapshot" in workflow
    assert "VITE_BASE_PATH: /${{ github.event.repository.name }}/" in workflow
    assert "cp -R web/dist/. site/" in workflow
    assert "npm run --prefix web build" in workflow
    assert "site/studio" in workflow
    assert "Add wiki redirect page" in workflow
    assert "site/docs/index.html" in workflow
    assert "/wiki" in workflow


def test_native_cmake_scaffold_present() -> None:
    root_cmake = _read("CMakeLists.txt")
    cpp_cmake = _read("cpp/CMakeLists.txt")
    cpp_source = _read("cpp/chapter_metrics.cpp")
    feature_metrics_source = _read("cpp/story_feature_metrics.cpp")
    assert "add_subdirectory(cpp)" in root_cmake
    assert "CMAKE_CXX_CLANG_TIDY" in root_cmake
    assert "CMAKE_CXX_CPPCHECK" in root_cmake
    assert "add_executable(chapter_metrics" in cpp_cmake
    assert "add_executable(story_feature_metrics" in cpp_cmake
    assert "chapter_metrics_demo" in cpp_cmake
    assert "story_feature_metrics_demo" in cpp_cmake
    assert "PrintMetricsJson" in cpp_source
    assert "ComputeFeatureMetrics" in feature_metrics_source


def test_native_quality_config_files_exist() -> None:
    assert (ROOT / ".clang-format").exists()
    assert (ROOT / ".clang-tidy").exists()
    assert (ROOT / ".gitattributes").exists()
    assert (ROOT / ".pre-commit-config.yaml").exists()
    assert (ROOT / "CODEOWNERS").exists()
    assert (ROOT / "CONTRIBUTING.md").exists()
    assert (ROOT / "SECURITY.md").exists()
    assert (ROOT / "LICENSE").exists()


def test_precommit_enforces_commit_and_push_quality() -> None:
    precommit = _read(".pre-commit-config.yaml")
    assert "check-added-large-files" in precommit
    assert "check-toml" in precommit
    assert "check-yaml" in precommit
    assert "--unsafe" in precommit
    assert "exclude: ^mkdocs\\.yml$" in precommit
    assert "cxx-format-fix" in precommit
    assert "cxx-format-check" in precommit
    assert "py-import-boundaries" in precommit
    assert "py-quality-pre-push" in precommit
    assert "tools/run_dev_tool.py ruff check --fix" in precommit
    assert "tools/run_dev_tool.py clang-format --dry-run --Werror" in precommit


def test_pr_template_contains_required_sections() -> None:
    template = _read(".github/pull_request_template.md")
    assert "## Summary" in template
    assert "## Linked Issues" in template
    assert "## Full Mode (Larger/Riskier Change)" in template
    assert "### Motivation / Context" in template
    assert "### What Changed" in template
    assert "### Tradeoffs and Risks" in template
    assert "### How This Was Tested" in template
    assert "## Compact Mode (Small/Low-Risk Change)" in template
    assert "### Change Notes" in template
    assert "### Validation" in template


def test_pr_template_workflow_exists_and_checks_sections() -> None:
    workflow = _read(".github/workflows/pr-template-check.yml")
    assert "name: PR Template Check" in workflow
    assert "name: pr-template" in workflow
    assert "## Summary" in workflow
    assert "## Linked Issues" in workflow
    assert "full_mode_sections" in workflow
    assert "compact_mode_sections" in workflow
    assert "### Motivation / Context" in workflow
    assert "### Change Notes" in workflow
    assert "either full mode sections or compact mode sections" in workflow
    assert "story_generator/issues" in workflow


def test_pyproject_exposes_story_collection_entrypoints() -> None:
    pyproject = _read("pyproject.toml")
    assert 'story-reference = "story_gen.cli.reference_pipeline:main"' in pyproject
    assert 'story-collect = "story_gen.cli.story_collector:main"' in pyproject
    assert 'story-video = "story_gen.cli.youtube_downloader:main"' in pyproject
    assert 'story-api = "story_gen.cli.api:main"' in pyproject
    assert 'story-blueprint = "story_gen.cli.blueprint:main"' in pyproject
    assert 'story-features = "story_gen.cli.features:main"' in pyproject


def test_mkdocs_configuration_exists() -> None:
    config = _read("mkdocs.yml")
    assert "site_name:" in config
    assert "nav:" in config
    assert "Architecture Diagrams:" in config
    assert "Contracts Registry:" in config
    assert "API:" in config
    assert "Developer Setup:" in config
    assert "Good Essay Mode:" in config
    assert "Deployment:" in config
    assert "Wiki Docs Sync:" in config
    assert "Observability:" in config
    assert "Studio:" in config
    assert "Droplet Stack:" in config
    assert "Feature Pipeline:" in config
    assert "Story Bundle:" in config
    assert "Graph Strategy:" in config
    assert "Architecture:" in config
    assert "ADR:" in config
    assert "logo: assets/brand/story-gen-mark.svg" in config
    assert "favicon: assets/brand/story-gen-favicon.svg" in config
    assert "scheme: slate" in config
    assert "Switch to light mode" in config
    assert "Switch to dark mode" in config
    assert "0012 Offline Studio Demo on Pages:" in config
    assert "0013 Bounded Observability and Anomaly Retention:" in config
    assert "0014 Graph Layout Contract and Storage Evaluation:" in config
    assert "0015 Dark Mode Default and Theme Toggle:" in config
    assert "0016 Native Feature Metrics Acceleration Path:" in config
    assert "0017 Story Bundle Binary Format:" in config
    assert "0019 Contract Registry and Pipeline Governance:" in config
    assert "0018 Wiki Docs + Product-First Pages:" in config
    assert "pymdownx.superfences" in config
    assert "mermaid.min.js" in config
    assert "javascripts/mermaid.js" in config


def test_pyproject_enforces_pytest_coverage_gate() -> None:
    pyproject = _read("pyproject.toml")
    assert "--cov=story_gen" in pyproject
    assert "--cov-fail-under=80" in pyproject


def test_pyproject_has_phased_nlp_dependency_groups() -> None:
    pyproject = _read("pyproject.toml")
    assert "nlp = [" in pyproject
    assert '"spacy>=' in pyproject
    assert '"sentence-transformers>=' in pyproject
    assert '"networkx>=' in pyproject
    assert "topic = [" in pyproject
    assert '"bertopic>=' in pyproject
    assert '"umap-learn>=' in pyproject
    assert '"hdbscan>=' in pyproject
    assert "advanced = [" in pyproject
    assert '"stanza>=' in pyproject


def test_argparse_boundaries_for_story_tools() -> None:
    collect_cli = _read("src/story_gen/cli/story_collector.py")
    reference_cli = _read("src/story_gen/cli/reference_pipeline.py")
    video_cli = _read("src/story_gen/cli/youtube_downloader.py")
    assert "import argparse" in collect_cli
    assert "import argparse" in reference_cli
    assert "import argparse" in video_cli
    assert not (ROOT / "src" / "story_gen" / "story_collector.py").exists()
    assert not (ROOT / "src" / "story_gen" / "reference_pipeline.py").exists()
    assert not (ROOT / "src" / "story_gen" / "youtube_downloader.py").exists()


def test_pre_push_checks_include_docs_and_cpp_format() -> None:
    checks = _read("src/story_gen/pre_push_checks.py")
    assert 'run_tool("pre-commit", "run", "--all-files")' in checks
    assert "uv executable not found in PATH" in checks
    assert "docker executable not found in PATH" in checks
    assert 'run_tool("mkdocs", "build", "--strict")' in checks
    assert '"npm", "run", "--prefix", "web", "typecheck"' in checks
    assert '"npm", "run", "--prefix", "web", "test:coverage"' in checks
    assert '"npm", "run", "--prefix", "web", "build"' in checks
    assert 'run_tool("clang-format", "--dry-run", "--Werror", *cpp_sources)' in checks
    assert '"docker/ci.Dockerfile"' in checks
    assert '"story-gen-ci-prepush"' in checks


def test_ci_dockerfile_installs_dev_group_only() -> None:
    dockerfile = _read("docker/ci.Dockerfile")
    assert "uv sync --group dev" in dockerfile
    assert "/usr/local/bin/uv" in dockerfile


def test_frontend_vitest_coverage_gate_exists() -> None:
    package_json = _read("web/package.json")
    vitest_config = _read("web/vitest.config.ts")
    assert '"dev:hot": "vite --host 127.0.0.1 --port 5174 --strictPort"' in package_json
    assert '"test:coverage": "vitest run --coverage"' in package_json
    assert '"@vitest/coverage-v8"' in package_json
    assert "thresholds" in vitest_config
    assert "lines: 80" in vitest_config


def test_architecture_docs_and_adr_scaffold_exist() -> None:
    assert (ROOT / "docs" / "architecture.md").exists()
    assert (ROOT / "docs" / "adr").is_dir()
    assert (ROOT / "docs" / "adr" / "README.md").exists()
    assert (ROOT / "docs" / "adr" / "0000-template.md").exists()
    assert (ROOT / "docs" / "adr" / "0002-nlp-stack-and-analysis-contract-scaffold.md").exists()
    assert (ROOT / "docs" / "adr" / "0003-pages-static-hosting-and-local-sqlite-api.md").exists()
    assert (ROOT / "docs" / "adr" / "0004-fastapi-backend-react-studio-and-token-auth.md").exists()
    assert (
        ROOT / "docs" / "adr" / "0005-digitalocean-droplet-and-s3-compatible-storage-plan.md"
    ).exists()
    assert (
        ROOT / "docs" / "adr" / "0006-story-first-feature-extraction-and-schema-enforcement.md"
    ).exists()
    assert (ROOT / "docs" / "adr" / "0007-frontend-coverage-gate.md").exists()
    assert (ROOT / "docs" / "adr" / "0008-good-essay-mode-product-surface.md").exists()
    assert (
        ROOT / "docs" / "adr" / "0009-story-intelligence-pipeline-and-dashboard-read-models.md"
    ).exists()
    assert (ROOT / "docs" / "adr" / "0010-docker-local-stack-and-ci-validation.md").exists()
    assert (ROOT / "docs" / "adr" / "0011-brand-icon-system-for-web-and-docs.md").exists()
    assert (ROOT / "docs" / "adr" / "0012-offline-studio-demo-on-github-pages.md").exists()
    assert (ROOT / "docs" / "adr" / "0013-bounded-observability-and-anomaly-retention.md").exists()
    assert (ROOT / "docs" / "adr" / "0014-graph-layout-contract-and-storage-evaluation.md").exists()
    assert (ROOT / "docs" / "adr" / "0015-dark-mode-default-and-toggle.md").exists()
    assert (ROOT / "docs" / "adr" / "0016-native-feature-metrics-acceleration-path.md").exists()
    assert (ROOT / "docs" / "adr" / "0017-story-bundle-binary-format.md").exists()
    assert (ROOT / "docs" / "adr" / "0019-contract-registry-and-pipeline-governance.md").exists()
    assert (ROOT / "docs" / "contracts_registry.md").exists()
    assert (ROOT / "docs" / "adr" / "0018-wiki-docs-and-product-first-pages.md").exists()
    assert (ROOT / "docs" / "story_bundle.md").exists()
    assert (ROOT / "docs" / "observability.md").exists()
    assert (ROOT / "docs" / "graph_strategy.md").exists()
    assert (ROOT / "docs" / "studio.md").exists()
    assert (ROOT / "docs" / "developer_setup.md").exists()
    assert (ROOT / "docs" / "github_collaboration.md").exists()
    assert (ROOT / "docs" / "wiki_docs.md").exists()
    assert (ROOT / "docs" / "essay_mode.md").exists()
    assert (ROOT / "docs" / "droplet_stack.md").exists()
    assert (ROOT / "docs" / "feature_pipeline.md").exists()
    assert (ROOT / "docs" / "architecture_diagrams.md").exists()
    assert (ROOT / "docs" / "javascripts" / "mermaid.js").exists()
    architecture = _read("docs/architecture.md")
    adr_0019 = _read("docs/adr/0019-contract-registry-and-pipeline-governance.md")
    assert "## Schema Versioning Policy" in architecture
    assert "story_analysis.v2" in architecture
    assert "## Version Migration Policy" in adr_0019
    assert "story_analysis.v2" in adr_0019


def test_api_docs_reference_swagger_and_openapi_endpoints() -> None:
    api_docs = _read("docs/api.md")
    setup_docs = _read("docs/developer_setup.md")
    assert "http://127.0.0.1:8000/docs" in api_docs
    assert "http://127.0.0.1:8000/redoc" in api_docs
    assert "http://127.0.0.1:8000/openapi.json" in api_docs
    assert "Authorize" in api_docs
    assert "http://127.0.0.1:8000/redoc" in setup_docs


def test_analysis_contract_scaffold_exists_and_is_valid_json() -> None:
    contracts_dir = ROOT / "work" / "contracts"
    expected_names = [
        "A_corpus_hygiene.json",
        "B_theme_motif.json",
        "C_voice_fingerprint.json",
        "D_character_consistency.json",
        "E_plot_causality.json",
        "F_canon_enforcement.json",
        "G_drift_robustness.json",
        "H_enrichment_data.json",
    ]
    assert (contracts_dir / "README.md").exists()
    for name in expected_names:
        path = contracts_dir / name
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["version"] == "0.1.0"
        assert payload["artifacts"]
    golden_story = ROOT / "tests" / "fixtures" / "story_analysis_v1_golden.json"
    assert golden_story.exists()
    payload = json.loads(golden_story.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "story_analysis.v1"


def test_policy_docs_require_failure_path_testing_rules() -> None:
    contributing = _read("CONTRIBUTING.md")
    agents = _read("AGENTS.md")
    assert "Tests must cover both success and failure paths" in contributing
    assert "Do not delete or weaken tests to make CI pass" in contributing
    assert "Do not remove tests to satisfy gates" in agents
    assert "## 10. Human PR Status Comments" in agents
    assert "Use this order: `current state`, `why`, `next step`." in agents
    assert "Keep comments short (3 to 6 lines)." in agents


def test_boundary_package_scaffolds_exist() -> None:
    assert (ROOT / "src" / "story_gen" / "api").is_dir()
    assert (ROOT / "src" / "story_gen" / "core").is_dir()
    assert (ROOT / "src" / "story_gen" / "adapters").is_dir()
    assert (ROOT / "src" / "story_gen" / "native").is_dir()
    assert (ROOT / "cpp" / "include").is_dir()
    assert (ROOT / "web").is_dir()
    assert (ROOT / "ops").is_dir()
    assert (ROOT / "ops" / "docker-compose.droplet.yml").exists()
    assert (ROOT / "ops" / "docker-compose.aws.yml").exists()
    assert (ROOT / "ops" / "docker-compose.gcp.yml").exists()
    assert (ROOT / "ops" / "docker-compose.azure.yml").exists()
    assert (ROOT / "ops" / "Caddyfile").exists()
    assert (ROOT / "ops" / ".env.example").exists()
    assert (ROOT / "ops" / ".env.aws.example").exists()
    assert (ROOT / "ops" / ".env.gcp.example").exists()
    assert (ROOT / "ops" / ".env.azure.example").exists()
    assert (ROOT / "tools" / "run_dev_tool.py").exists()
    assert (ROOT / "tools" / "pr_flow.py").exists()
    assert (ROOT / "tools" / "sync_wiki.py").exists()
    assert (ROOT / "tools" / "export_contract_registry.py").exists()
    assert (ROOT / ".dockerignore").exists()
    assert (ROOT / "docker-compose.yml").exists()
    assert (ROOT / "docker" / "api.Dockerfile").exists()
    assert (ROOT / "docker" / "web.Dockerfile").exists()
    assert (ROOT / "docker" / "ci.Dockerfile").exists()
    assert (ROOT / "tools" / "generate_brand_icons.py").exists()
    assert (ROOT / ".github" / "pull_request_template.md").exists()
    assert (ROOT / ".github" / "labeler.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "task.yml").exists()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").exists()
    assert (ROOT / ".github" / "workflows" / "pr-labeler.yml").exists()
    assert (ROOT / ".github" / "workflows" / "pr-template-check.yml").exists()
    assert (ROOT / "web" / "public" / "favicon.svg").exists()
    assert (ROOT / "web" / "public" / "favicon.ico").exists()
    assert (ROOT / "web" / "public" / "site.webmanifest").exists()


def test_pr_flow_supports_explicit_or_fallback_gh_binary() -> None:
    script = _read("tools/pr_flow.py")
    assert "GH_BIN" in script
    assert "GitHub CLI\\gh.exe" in script
    assert "PR_DEFAULT_REVIEWER" in script
    assert "Skipped reviewer" in script
    assert (ROOT / "web" / "public" / "icons" / "icon-16.png").exists()
    assert (ROOT / "web" / "public" / "icons" / "icon-32.png").exists()
    assert (ROOT / "web" / "public" / "icons" / "icon-192.png").exists()
    assert (ROOT / "web" / "public" / "icons" / "icon-512.png").exists()
    assert (ROOT / "docs" / "assets" / "brand" / "story-gen-mark.svg").exists()
    assert (ROOT / "docs" / "assets" / "brand" / "story-gen-favicon.svg").exists()
    assert (ROOT / "work" / "contracts" / "story_pipeline_contract_registry.v1.json").exists()


def test_gitattributes_enforces_cross_platform_line_endings() -> None:
    gitattributes = _read(".gitattributes")
    assert "* text=auto eol=lf" in gitattributes
    assert "*.ps1 text eol=crlf" in gitattributes
    assert "*.png binary" in gitattributes


def test_no_utils_module_names() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        assert path.name != "utils.py", str(path.relative_to(ROOT))


def test_todo_requires_issue_reference() -> None:
    scan_roots = [ROOT / "src", ROOT / "tests", ROOT / "docs"]
    excluded = {
        (ROOT / "tests" / "test_project_contracts.py").resolve(),
    }
    for root in scan_roots:
        for path in root.rglob("*"):
            if path.resolve() in excluded:
                continue
            if path.suffix not in {".py", ".md", ".yml", ".yaml", ".toml"}:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if "TODO" not in line:
                    continue
                assert "TODO(#" in line, f"{path.relative_to(ROOT)}: {line.strip()}"
