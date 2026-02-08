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


def test_ci_workflow_includes_code_quality_steps() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "Pre-commit hooks (all files)" in workflow
    assert "uv lock --check" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run ruff format --check ." in workflow
    assert "uv run mypy" in workflow
    assert "uv run pytest" in workflow
    assert "uv run mkdocs build --strict" in workflow
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


def test_pyproject_exposes_story_collection_entrypoints() -> None:
    pyproject = _read("pyproject.toml")
    assert 'story-reference = "story_gen.cli.reference:main"' in pyproject
    assert 'story-collect = "story_gen.cli.collect:main"' in pyproject
    assert 'story-video = "story_gen.cli.video:main"' in pyproject
    assert 'story-api = "story_gen.cli.api:main"' in pyproject


def test_mkdocs_configuration_exists() -> None:
    config = _read("mkdocs.yml")
    assert "site_name:" in config
    assert "nav:" in config
    assert "API:" in config


def test_pyproject_enforces_pytest_coverage_gate() -> None:
    pyproject = _read("pyproject.toml")
    assert "--cov=story_gen" in pyproject
    assert "--cov-fail-under=80" in pyproject


def test_argparse_boundaries_for_story_tools() -> None:
    collect_core = _read("src/story_gen/story_collector.py")
    reference_core = _read("src/story_gen/reference_pipeline.py")
    video_core = _read("src/story_gen/youtube_downloader.py")
    collect_cli = _read("src/story_gen/cli/collect.py")
    reference_cli = _read("src/story_gen/cli/reference.py")
    video_cli = _read("src/story_gen/cli/video.py")
    assert "import argparse" not in collect_core
    assert "import argparse" not in reference_core
    assert "import argparse" not in video_core
    assert "import argparse" in collect_cli
    assert "import argparse" in reference_cli
    assert "import argparse" in video_cli
