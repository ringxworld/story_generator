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
    assert "collect-story:" in makefile
    assert "video-story:" in makefile
    assert "import-check:" in makefile
    assert "quality: lock-check import-check" in makefile


def test_ci_workflow_includes_code_quality_steps() -> None:
    workflow = _read(".github/workflows/ci.yml")
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


def test_deploy_workflow_requires_ci_success() -> None:
    workflow = _read(".github/workflows/deploy-pages.yml")
    assert "workflow_run:" in workflow
    assert "workflows:" in workflow
    assert "- CI" in workflow
    assert "conclusion == 'success'" in workflow
    assert "head_branch == 'main'" in workflow
    assert "uv run mkdocs build --strict" in workflow


def test_native_cmake_scaffold_present() -> None:
    root_cmake = _read("CMakeLists.txt")
    cpp_cmake = _read("cpp/CMakeLists.txt")
    cpp_source = _read("cpp/chapter_metrics.cpp")
    assert "add_subdirectory(cpp)" in root_cmake
    assert "CMAKE_CXX_CLANG_TIDY" in root_cmake
    assert "CMAKE_CXX_CPPCHECK" in root_cmake
    assert "add_executable(chapter_metrics" in cpp_cmake
    assert "chapter_metrics_demo" in cpp_cmake
    assert "PrintMetricsJson" in cpp_source


def test_native_quality_config_files_exist() -> None:
    assert (ROOT / ".clang-format").exists()
    assert (ROOT / ".clang-tidy").exists()
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
    assert "cxx-format-fix" in precommit
    assert "cxx-format-check" in precommit
    assert "py-import-boundaries" in precommit
    assert "py-quality-pre-push" in precommit


def test_pyproject_exposes_story_collection_entrypoints() -> None:
    pyproject = _read("pyproject.toml")
    assert 'story-reference = "story_gen.cli.reference_pipeline:main"' in pyproject
    assert 'story-collect = "story_gen.cli.story_collector:main"' in pyproject
    assert 'story-video = "story_gen.cli.youtube_downloader:main"' in pyproject
    assert 'story-api = "story_gen.cli.api:main"' in pyproject


def test_mkdocs_configuration_exists() -> None:
    config = _read("mkdocs.yml")
    assert "site_name:" in config
    assert "nav:" in config
    assert "API:" in config
    assert "Architecture:" in config
    assert "ADR:" in config


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
    assert '"uv", "run", "python", "tools/check_imports.py"' in checks
    assert '"uv", "run", "mkdocs", "build", "--strict"' in checks
    assert '"uv", "run", "clang-format", "--dry-run", "--Werror"' in checks


def test_architecture_docs_and_adr_scaffold_exist() -> None:
    assert (ROOT / "docs" / "architecture.md").exists()
    assert (ROOT / "docs" / "adr").is_dir()
    assert (ROOT / "docs" / "adr" / "README.md").exists()
    assert (ROOT / "docs" / "adr" / "0000-template.md").exists()
    assert (ROOT / "docs" / "adr" / "0002-nlp-stack-and-analysis-contract-scaffold.md").exists()


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


def test_policy_docs_require_failure_path_testing_rules() -> None:
    contributing = _read("CONTRIBUTING.md")
    agents = _read("AGENTS.md")
    assert "Tests must cover both success and failure paths" in contributing
    assert "Do not delete or weaken tests to make CI pass" in contributing
    assert "Do not remove tests to satisfy gates" in agents


def test_boundary_package_scaffolds_exist() -> None:
    assert (ROOT / "src" / "story_gen" / "api").is_dir()
    assert (ROOT / "src" / "story_gen" / "core").is_dir()
    assert (ROOT / "src" / "story_gen" / "adapters").is_dir()
    assert (ROOT / "src" / "story_gen" / "native").is_dir()
    assert (ROOT / "cpp" / "include").is_dir()


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
