"""CLI runner for static site generation."""

from __future__ import annotations

from story_gen.site_builder import build_site


def main() -> None:
    output_path = build_site()
    print(f"Built site page at {output_path}")


if __name__ == "__main__":
    main()
