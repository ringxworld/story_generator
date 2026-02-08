"""CLI for video-story ingestion."""

from __future__ import annotations

import argparse

from story_gen.youtube_downloader import VideoStoryArgs, run_video_story_pipeline


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


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    parsed = parser.parse_args(argv)
    run_video_story_pipeline(_args_from_namespace(parsed))


if __name__ == "__main__":
    main()
