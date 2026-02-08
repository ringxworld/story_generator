import json
from argparse import Namespace
from pathlib import Path
from typing import Literal, Mapping, cast

import httpx
import pytest

from story_gen.cli.reference import _pipeline_args_from_namespace
from story_gen.cli.reference import main as reference_cli_main
from story_gen.reference_pipeline import (
    EpisodeRecord,
    LibreTranslateTranslator,
    PipelineArgs,
    _chunk_text,
    _episode_record_from_loaded,
    _translated_text_from_loaded,
    build_analysis,
    parse_episode_page,
    parse_index_page,
    run_pipeline,
)


def test_parse_index_page_extracts_episode_and_last_page() -> None:
    html = """
    <html>
      <body>
        <a href="/n2267be/?p=8" class="c-pager__item c-pager__item--last">Last</a>
        <div class="p-eplist">
          <div class="p-eplist__chapter-title">Arc One</div>
          <div class="p-eplist__sublist">
            <a href="/n2267be/1/" class="p-eplist__subtitle">Prologue</a>
            <div class="p-eplist__update">
              2012/04/20 21:58
              <span title="2012/09/01 20:09 revised">(rev)</span>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    episodes, last_page = parse_index_page(html, "https://ncode.syosetu.com/n2267be/")
    assert last_page == 8
    assert len(episodes) == 1
    assert episodes[0].episode_number == 1
    assert episodes[0].title_jp == "Prologue"
    assert episodes[0].arc_title_jp == "Arc One"
    assert episodes[0].published_at == "2012/04/20 21:58"
    assert episodes[0].revised_at == "2012/09/01 20:09"


def test_parse_episode_page_extracts_title_body_and_total_hint() -> None:
    html = """
    <html>
      <body>
        <div class="p-novel__number">1/761</div>
        <h1 class="p-novel__title">Episode Title</h1>
        <div class="js-novel-text p-novel__text">
          <p>Line 1</p>
          <p><br /></p>
          <p>Line 2</p>
        </div>
      </body>
    </html>
    """
    title, body, total_hint = parse_episode_page(html)
    assert title == "Episode Title"
    assert "Line 1" in body
    assert "Line 2" in body
    assert total_hint == 761


def test_chunk_text_splits_long_text() -> None:
    text = "a" * 10 + "\n\n" + "b" * 10 + "\n\n" + "c" * 10
    chunks = _chunk_text(text, max_chars=15)
    assert len(chunks) >= 2


def test_build_analysis_counts_focus_names() -> None:
    episodes = [
        EpisodeRecord(
            episode_number=1,
            title_jp="a",
            arc_title_jp="arc",
            url="u",
            published_at=None,
            revised_at=None,
            total_episodes_hint=2,
            text_jp='Subaru said "hello".',
        ),
        EpisodeRecord(
            episode_number=2,
            title_jp="b",
            arc_title_jp="arc",
            url="u",
            published_at=None,
            revised_at=None,
            total_episodes_hint=2,
            text_jp="Emilia smiled.",
        ),
    ]
    analysis = build_analysis(episodes, focus_names=["Subaru", "Emilia"])
    mentions = analysis["focus_name_mentions"]
    assert mentions["Subaru"] == 1
    assert mentions["Emilia"] == 1


class _FakeResponse:
    def __init__(self, *, text: str = "", json_payload: object = None) -> None:
        self.text = text
        self._json_payload = {} if json_payload is None else json_payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._json_payload


class _FakeClient:
    def __init__(
        self,
        *,
        get_map: dict[str, str],
        post_map: dict[str, object] | None = None,
    ) -> None:
        self.get_map = get_map
        self.post_map = post_map or {}
        self.get_calls: list[str] = []
        self.post_calls: list[str] = []
        self.post_payloads: list[Mapping[str, object]] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        return False

    def get(self, url: str) -> _FakeResponse:
        self.get_calls.append(url)
        if url not in self.get_map:
            raise AssertionError(f"Unexpected GET url: {url}")
        return _FakeResponse(text=self.get_map[url])

    def post(self, url: str, json: Mapping[str, object]) -> _FakeResponse:
        self.post_calls.append(url)
        self.post_payloads.append(json)
        if url not in self.post_map:
            raise AssertionError(f"Unexpected POST url: {url}")
        return _FakeResponse(json_payload=self.post_map[url])


def _base_args(tmp_path: Path, **overrides: object) -> PipelineArgs:
    base_url_override = overrides.get("base_url")
    base_url = (
        str(base_url_override) if base_url_override is not None else "https://example.com/n1234aa/"
    )
    return PipelineArgs(
        base_url=base_url,
        work_dir=str(tmp_path / "work"),
        project_id="fixture",
        start_page=1,
        end_page=None,
        episode_start=1,
        episode_end=None,
        max_episodes=None,
        crawl_delay_seconds=0.0,
        force_fetch=False,
        translate_provider="none",
        source_language="ja",
        target_language="en",
        libretranslate_url="http://localhost:5000",
        libretranslate_api_key=None,
        translate_delay_seconds=0.0,
        translate_chunk_size=1000,
        force_translate=False,
        sample_count=1,
        excerpt_chars=80,
        analysis_names="",
    )


def test_cli_main_normalizes_optional_args(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, PipelineArgs] = {}

    def fake_run_pipeline(args: PipelineArgs) -> None:
        captured["args"] = args

    monkeypatch.setattr("story_gen.cli.reference.run_pipeline", fake_run_pipeline)

    reference_cli_main(
        [
            "--end-page",
            "0",
            "--episode-end",
            "0",
            "--max-episodes",
            "0",
            "--libretranslate-api-key",
            "",
        ]
    )

    args = captured["args"]
    assert args.end_page is None
    assert args.episode_end is None
    assert args.max_episodes is None
    assert args.libretranslate_api_key is None


def test_pipeline_args_from_namespace_normalizes_values() -> None:
    namespace = Namespace(
        base_url="https://example.com/n1234aa/",
        work_dir="work",
        project_id="",
        start_page=0,
        end_page=0,
        episode_start=0,
        episode_end=0,
        max_episodes=0,
        crawl_delay_seconds=1.1,
        force_fetch=False,
        translate_provider="libretranslate",
        source_language="ja",
        target_language="en",
        libretranslate_url="http://localhost:5000",
        libretranslate_api_key="",
        translate_delay_seconds=0.2,
        translate_chunk_size=1200,
        force_translate=False,
        sample_count=0,
        excerpt_chars=0,
        analysis_names="",
    )
    args = _pipeline_args_from_namespace(namespace)
    assert args.start_page == 1
    assert args.episode_start == 1
    assert args.end_page is None
    assert args.episode_end is None
    assert args.max_episodes is None
    assert args.sample_count == 1
    assert args.excerpt_chars == 1
    assert args.libretranslate_api_key is None
    assert args.translate_provider == "libretranslate"


def test_run_pipeline_creates_expected_output_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "https://example.com/n1234aa/"
    episode_url = f"{base_url}1/"
    index_html = """
    <html><body>
      <div class="p-eplist">
        <div class="p-eplist__chapter-title">Arc 1</div>
        <div class="p-eplist__sublist">
          <a href="/n1234aa/1/" class="p-eplist__subtitle">Episode One</a>
          <div class="p-eplist__update">2024/01/01 00:00</div>
        </div>
      </div>
    </body></html>
    """
    episode_html = """
    <html><body>
      <div class="p-novel__number">1/10</div>
      <h1 class="p-novel__title">Episode One</h1>
      <div class="js-novel-text p-novel__text">
        <p>Line one.</p>
        <p><br /></p>
        <p>Line two.</p>
      </div>
    </body></html>
    """
    fake_client = _FakeClient(get_map={base_url: index_html, episode_url: episode_html})
    monkeypatch.setattr("story_gen.reference_pipeline.httpx.Client", lambda **kwargs: fake_client)

    args = _base_args(tmp_path, base_url=base_url)
    run_pipeline(args)

    output_root = tmp_path / "work" / "reference_data" / "fixture"
    assert (output_root / "meta" / "index.json").exists()
    assert (output_root / "raw" / "0001.json").exists()
    assert (output_root / "samples" / "story_sample.md").exists()
    assert (output_root / "analysis" / "analysis.md").exists()

    raw_payload = json.loads((output_root / "raw" / "0001.json").read_text(encoding="utf-8"))
    assert raw_payload["title_jp"] == "Episode One"
    assert "Line one." in raw_payload["text_jp"]


def test_run_pipeline_prefers_cached_raw_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "https://example.com/n1234aa/"
    index_html = """
    <html><body>
      <div class="p-eplist">
        <div class="p-eplist__chapter-title">Arc 1</div>
        <div class="p-eplist__sublist">
          <a href="/n1234aa/1/" class="p-eplist__subtitle">Episode One</a>
          <div class="p-eplist__update">2024/01/01 00:00</div>
        </div>
      </div>
    </body></html>
    """
    fake_client = _FakeClient(get_map={base_url: index_html})
    monkeypatch.setattr("story_gen.reference_pipeline.httpx.Client", lambda **kwargs: fake_client)

    args = _base_args(tmp_path, base_url=base_url)
    output_root = tmp_path / "work" / "reference_data" / "fixture"
    raw_file = output_root / "raw" / "0001.json"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        json.dumps(
            {
                "episode_number": 1,
                "title_jp": "Cached Episode",
                "arc_title_jp": "Arc 1",
                "url": f"{base_url}1/",
                "published_at": "2024/01/01 00:00",
                "revised_at": None,
                "total_episodes_hint": 10,
                "text_jp": "Cached line.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    run_pipeline(args)

    assert fake_client.get_calls == [base_url]
    sample_text = (output_root / "samples" / "story_sample.md").read_text(encoding="utf-8")
    assert "Cached Episode" in sample_text


def test_run_pipeline_with_libretranslate_writes_translation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "https://example.com/n1234aa/"
    episode_url = f"{base_url}1/"
    index_html = """
    <html><body>
      <div class="p-eplist">
        <div class="p-eplist__chapter-title">Arc 1</div>
        <div class="p-eplist__sublist">
          <a href="/n1234aa/1/" class="p-eplist__subtitle">Episode One</a>
          <div class="p-eplist__update">2024/01/01 00:00</div>
        </div>
      </div>
    </body></html>
    """
    episode_html = """
    <html><body>
      <div class="p-novel__number">1/10</div>
      <h1 class="p-novel__title">Episode One</h1>
      <div class="js-novel-text p-novel__text">
        <p>Line one.</p>
      </div>
    </body></html>
    """
    post_url = "http://localhost:5000/translate"
    fake_client = _FakeClient(
        get_map={base_url: index_html, episode_url: episode_html},
        post_map={post_url: {"translatedText": "Translated line one."}},
    )
    monkeypatch.setattr("story_gen.reference_pipeline.httpx.Client", lambda **kwargs: fake_client)
    monkeypatch.setattr("story_gen.reference_pipeline.time.sleep", lambda _x: None)

    args = PipelineArgs(
        **{
            **_base_args(tmp_path, base_url=base_url).__dict__,
            "translate_provider": "libretranslate",
        }
    )
    run_pipeline(args)

    output_root = tmp_path / "work" / "reference_data" / "fixture"
    translation_payload = json.loads(
        (output_root / "translated_en" / "0001.json").read_text(encoding="utf-8")
    )
    assert translation_payload["text_translated"] == "Translated line one."
    sample_text = (output_root / "samples" / "story_sample.md").read_text(encoding="utf-8")
    assert "English excerpt (machine translation)" in sample_text


def test_libretranslate_translator_raises_for_invalid_payload() -> None:
    fake_client = _FakeClient(
        get_map={},
        post_map={"http://localhost:5000/translate": {"unexpected": "shape"}},
    )
    translator = LibreTranslateTranslator(
        client=cast(httpx.Client, fake_client),
        base_url="http://localhost:5000",
    )
    with pytest.raises(RuntimeError, match="translatedText"):
        translator.translate("hello")


def test_episode_record_from_loaded_rejects_bad_types() -> None:
    with pytest.raises(RuntimeError, match="episode_number"):
        _episode_record_from_loaded(
            {
                "episode_number": True,
                "title_jp": "t",
                "arc_title_jp": None,
                "url": "u",
                "published_at": None,
                "revised_at": None,
                "total_episodes_hint": None,
                "text_jp": "x",
            }
        )


def test_translated_text_from_loaded_handles_non_dict() -> None:
    assert _translated_text_from_loaded("not-a-dict") is None


def test_build_analysis_for_empty_input_has_message() -> None:
    analysis = build_analysis([], [])
    assert analysis["episode_count"] == 0
    assert analysis["message"] == "No episodes available for analysis."
