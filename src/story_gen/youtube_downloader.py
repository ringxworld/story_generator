"""Download video audio and optionally create Whisper transcripts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from story_gen.pipelines.results import VideoStoryResult

AudioFormat = Literal["mp3", "m4a", "wav", "flac", "opus"]
WhisperTask = Literal["transcribe", "translate"]


@dataclass(frozen=True)
class VideoStoryArgs:
    url: str
    output_dir: str
    audio_format: AudioFormat
    transcribe: bool
    whisper_model: str
    whisper_language: str
    whisper_task: WhisperTask
    whisper_binary: str


def run_streaming(command: list[str]) -> None:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line.rstrip("\n"))
    code = process.wait()
    if code != 0:
        raise RuntimeError(f"Command failed with exit code {code}: {' '.join(command)}")


def build_ytdlp_command(args: VideoStoryArgs) -> list[str]:
    output_template = str(Path(args.output_dir) / "%(title)s.%(ext)s")
    return [
        "yt-dlp",
        "--newline",
        "--no-write-thumbnail",
        "--no-embed-thumbnail",
        "--extract-audio",
        "--audio-format",
        args.audio_format,
        "-o",
        output_template,
        args.url,
    ]


def build_whisper_command(args: VideoStoryArgs, audio_path: Path) -> list[str]:
    return [
        args.whisper_binary,
        str(audio_path),
        "--model",
        args.whisper_model,
        "--language",
        args.whisper_language,
        "--task",
        args.whisper_task,
        "--output_format",
        "txt",
        "--output_dir",
        str(Path(args.output_dir)),
    ]


def newest_file(path: Path) -> Path:
    files = [item for item in path.iterdir() if item.is_file()]
    if not files:
        raise RuntimeError(f"No files found in {path}")
    return max(files, key=lambda item: item.stat().st_mtime)


def ensure_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(f"Missing required binary: {binary}")


def run_video_story_pipeline(args: VideoStoryArgs) -> VideoStoryResult:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ensure_binary("yt-dlp")
    print("[video] downloading audio with yt-dlp")
    run_streaming(build_ytdlp_command(args))

    audio_path = newest_file(output_dir)
    transcript_path: Path | None = None

    if args.transcribe:
        ensure_binary(args.whisper_binary)
        print("[video] creating transcript with whisper")
        run_streaming(build_whisper_command(args, audio_path))
        candidate = output_dir / f"{audio_path.stem}.txt"
        if candidate.exists():
            transcript_path = candidate
        else:
            print("[video] whisper completed but transcript file was not found by name convention")

    print(f"[video] audio: {audio_path}")
    if transcript_path:
        print(f"[video] transcript: {transcript_path}")
    return VideoStoryResult(
        output_dir=output_dir,
        audio_path=audio_path,
        transcript_path=transcript_path,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download YouTube audio for story study and optionally transcribe with Whisper.",
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", default="work/video_story")
    parser.add_argument(
        "--audio-format",
        choices=["mp3", "m4a", "wav", "flac", "opus"],
        default="mp3",
    )
    parser.add_argument("--transcribe", action="store_true")
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--whisper-language", default="ja")
    parser.add_argument("--whisper-task", choices=["transcribe", "translate"], default="transcribe")
    parser.add_argument("--whisper-binary", default="whisper")
    return parser


def _args_from_namespace(namespace: argparse.Namespace) -> VideoStoryArgs:
    return VideoStoryArgs(
        url=str(namespace.url),
        output_dir=str(namespace.output_dir),
        audio_format=namespace.audio_format,
        transcribe=bool(namespace.transcribe),
        whisper_model=str(namespace.whisper_model),
        whisper_language=str(namespace.whisper_language),
        whisper_task=namespace.whisper_task,
        whisper_binary=str(namespace.whisper_binary),
    )


def cli_main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    args = _args_from_namespace(parsed)
    run_video_story_pipeline(args)
