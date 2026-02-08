from __future__ import annotations

import os
from pathlib import Path

import pytest

from story_gen.cli.youtube_downloader import _args_from_namespace
from story_gen.youtube_downloader import (
    VideoStoryArgs,
    build_whisper_command,
    build_ytdlp_command,
    ensure_binary,
    newest_file,
    run_video_story_pipeline,
)


def _base_args(tmp_path: Path) -> VideoStoryArgs:
    return VideoStoryArgs(
        url="https://www.youtube.com/watch?v=abc123",
        output_dir=str(tmp_path / "video"),
        audio_format="mp3",
        transcribe=False,
        whisper_model="small",
        whisper_language="ja",
        whisper_task="transcribe",
        whisper_binary="whisper",
    )


def test_build_ytdlp_command_includes_audio_extraction(tmp_path: Path) -> None:
    args = _base_args(tmp_path)
    command = build_ytdlp_command(args)
    assert "--extract-audio" in command
    assert "--audio-format" in command
    assert "mp3" in command
    assert args.url in command


def test_build_whisper_command_uses_expected_flags(tmp_path: Path) -> None:
    args = _base_args(tmp_path)
    audio = tmp_path / "video" / "sample.mp3"
    command = build_whisper_command(args, audio)
    assert command[0] == "whisper"
    assert "--model" in command
    assert "--language" in command
    assert "--task" in command
    assert "--output_format" in command
    assert "txt" in command


def test_newest_file_selects_latest(tmp_path: Path) -> None:
    output = tmp_path / "video"
    output.mkdir()
    first = output / "a.mp3"
    second = output / "b.mp3"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    os.utime(first, (1000, 1000))
    os.utime(second, (2000, 2000))
    assert newest_file(output) == second


def test_run_video_story_pipeline_with_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = VideoStoryArgs(
        **{
            **_base_args(tmp_path).__dict__,
            "transcribe": True,
        }
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_file = output_dir / "clip.mp3"
    transcript_file = output_dir / "clip.txt"
    audio_file.write_text("audio", encoding="utf-8")
    transcript_file.write_text("transcript", encoding="utf-8")

    invoked: list[list[str]] = []

    def fake_run_streaming(command: list[str]) -> None:
        invoked.append(command)

    monkeypatch.setattr("story_gen.youtube_downloader.ensure_binary", lambda _name: None)
    monkeypatch.setattr("story_gen.youtube_downloader.run_streaming", fake_run_streaming)
    monkeypatch.setattr("story_gen.youtube_downloader.newest_file", lambda _path: audio_file)

    result = run_video_story_pipeline(args)
    assert result.output_dir == output_dir
    assert result.audio_path == audio_file
    assert result.transcript_path == transcript_file
    assert len(invoked) == 2


def test_ensure_binary_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("story_gen.youtube_downloader.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Missing required binary"):
        ensure_binary("yt-dlp")


def test_args_from_namespace_builds_dataclass() -> None:
    namespace = type("NamespaceLike", (), {})()
    namespace.url = "https://example.com/v"
    namespace.output_dir = "work/video_story"
    namespace.audio_format = "wav"
    namespace.transcribe = True
    namespace.whisper_model = "small"
    namespace.whisper_language = "ja"
    namespace.whisper_task = "transcribe"
    namespace.whisper_binary = "whisper"
    args = _args_from_namespace(namespace)
    assert args.url == "https://example.com/v"
    assert args.audio_format == "wav"
    assert args.transcribe is True
