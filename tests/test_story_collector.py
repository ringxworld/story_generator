from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from story_gen.cli.story_collector import _args_from_namespace
from story_gen.story_collector import (
    StoryCollectorArgs,
    _index_page_url,
    collect_chapter_links,
    run_story_collection,
)


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeClient:
    def __init__(self, get_map: dict[str, str]) -> None:
        self.get_map = get_map
        self.calls: list[str] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        return False

    def get(self, url: str) -> _FakeResponse:
        self.calls.append(url)
        if url not in self.get_map:
            raise AssertionError(f"Unexpected URL: {url}")
        return _FakeResponse(self.get_map[url])


def test_index_page_url_formats_page_query() -> None:
    assert (
        _index_page_url("https://ncode.syosetu.com", "n1234ab", 1)
        == "https://ncode.syosetu.com/n1234ab/"
    )
    assert (
        _index_page_url("https://ncode.syosetu.com", "n1234ab", 3)
        == "https://ncode.syosetu.com/n1234ab/?p=3"
    )


def test_story_collection_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "https://example.com"
    series = "n1234ab"
    index_url = f"{base_url}/{series}/"
    chapter_url = f"{base_url}/{series}/1/"
    index_html = f"""
    <html><body>
      <div class="p-eplist">
        <div class="p-eplist__sublist">
          <a href="/{series}/1/" class="p-eplist__subtitle">Episode One</a>
          <div class="p-eplist__update">2024/01/01 00:00</div>
        </div>
      </div>
    </body></html>
    """
    chapter_html = """
    <html><body>
      <h1 class="p-novel__title">Chapter One</h1>
      <div class="js-novel-text p-novel__text">
        <p>Hello world.</p>
      </div>
    </body></html>
    """
    fake_client = _FakeClient({index_url: index_html, chapter_url: chapter_html})
    monkeypatch.setattr("story_gen.story_collector.httpx.Client", lambda **kwargs: fake_client)
    monkeypatch.setattr("story_gen.story_collector.time.sleep", lambda _x: None)

    args = StoryCollectorArgs(
        base_url=base_url,
        series_code=series,
        output_dir=str(tmp_path / "out"),
        output_filename="full_story.txt",
        chapter_start=1,
        chapter_end=None,
        max_chapters=None,
        crawl_delay_seconds=0.0,
        max_workers=1,
        timeout_seconds=30.0,
        user_agent="test-agent",
    )

    result = run_story_collection(args)
    assert result.output_root.exists()
    assert result.chapter_count == 1
    full_story = result.full_story_path.read_text(encoding="utf-8")
    assert "Chapter One" in full_story
    assert "Hello world." in full_story

    index_payload = json.loads(result.index_path.read_text(encoding="utf-8"))
    assert index_payload["chapter_count"] == 1
    assert index_payload["chapters"][0]["number"] == 1


def test_args_from_namespace_normalizes_ranges() -> None:
    namespace = type("NamespaceLike", (), {})()
    namespace.base_url = "https://example.com"
    namespace.series_code = "/N1234AB/"
    namespace.output_dir = "work/story_collector"
    namespace.output_filename = "full_story.txt"
    namespace.chapter_start = 0
    namespace.chapter_end = 0
    namespace.max_chapters = 0
    namespace.crawl_delay_seconds = -1
    namespace.max_workers = 0
    namespace.timeout_seconds = 0
    namespace.user_agent = "ua"

    args = _args_from_namespace(namespace)
    assert args.series_code == "n1234ab"
    assert args.chapter_start == 1
    assert args.chapter_end is None
    assert args.max_chapters is None
    assert args.crawl_delay_seconds == 0.0
    assert args.max_workers == 1
    assert args.timeout_seconds == 1.0


def test_collect_chapter_links_honors_range_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "https://example.com"
    series = "n1234ab"
    index_url = f"{base_url}/{series}/"
    index_html = f"""
    <html><body>
      <div class="p-eplist">
        <div class="p-eplist__sublist">
          <a href="/{series}/1/" class="p-eplist__subtitle">Episode One</a>
          <div class="p-eplist__update">2024/01/01 00:00</div>
        </div>
        <div class="p-eplist__sublist">
          <a href="/{series}/2/" class="p-eplist__subtitle">Episode Two</a>
          <div class="p-eplist__update">2024/01/02 00:00</div>
        </div>
      </div>
    </body></html>
    """
    fake_client = _FakeClient({index_url: index_html})
    monkeypatch.setattr("story_gen.story_collector.httpx.Client", lambda **kwargs: fake_client)

    args = StoryCollectorArgs(
        base_url=base_url,
        series_code=series,
        output_dir="work/story_collector",
        output_filename="full_story.txt",
        chapter_start=2,
        chapter_end=None,
        max_chapters=1,
        crawl_delay_seconds=0.0,
        max_workers=1,
        timeout_seconds=30.0,
        user_agent="test-agent",
    )

    links = collect_chapter_links(args)
    assert [link.number for link in links] == [2]
    assert links[0].title == "Episode Two"
