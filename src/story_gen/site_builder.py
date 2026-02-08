"""Static site builder for publishing story content to GitHub Pages."""

from __future__ import annotations

from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "content" / "story.md"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "site"
DEFAULT_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "index.html"


def markdown_to_html(markdown: str) -> str:
    """Convert a narrow markdown subset into escaped HTML blocks.

    The renderer is intentionally small because we only need predictable output
    for project publishing pages.
    """
    lines = markdown.splitlines()
    html_lines: list[str] = []
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        """Emit the current paragraph buffer as a single `<p>` block."""
        if paragraph_buffer:
            text = " ".join(part.strip() for part in paragraph_buffer if part.strip())
            if text:
                html_lines.append(f"<p>{escape(text)}</p>")
            paragraph_buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            html_lines.append(f"<h3>{escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            html_lines.append(f"<h2>{escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            html_lines.append(f"<h1>{escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            html_lines.append(f"<li>{escape(stripped[2:])}</li>")
            continue
        paragraph_buffer.append(line)

    flush_paragraph()

    normalized: list[str] = []
    in_list = False
    for line in html_lines:
        # Turn a stream of `<li>` tags into a proper `<ul>` section.
        if line.startswith("<li>"):
            if not in_list:
                normalized.append("<ul>")
                in_list = True
            normalized.append(line)
        else:
            if in_list:
                normalized.append("</ul>")
                in_list = False
            normalized.append(line)
    if in_list:
        normalized.append("</ul>")

    return "\n".join(normalized)


def build_page(body_html: str) -> str:
    """Wrap chapter HTML in a single self-contained page template."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>story_gen | Story</title>
  <style>
    :root {{
      color-scheme: light;
      --paper: #f8f5ef;
      --ink: #1c1a17;
      --accent: #9d4f2c;
      --frame: #d9ccb8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at 20% 0%, #fdfbf8 0%, transparent 45%),
        linear-gradient(180deg, #f2e8d8 0%, #ede1cd 100%);
      color: var(--ink);
    }}
    .shell {{
      max-width: 840px;
      margin: 2.5rem auto;
      background: var(--paper);
      border: 1px solid var(--frame);
      border-radius: 10px;
      box-shadow: 0 12px 32px rgba(40, 28, 16, 0.12);
      overflow: hidden;
    }}
    .titlebar {{
      padding: 1rem 1.4rem;
      background: linear-gradient(90deg, #2f251f, #59453b);
      color: #f8efe2;
      letter-spacing: 0.03em;
      font-size: 0.95rem;
      text-transform: uppercase;
    }}
    .content {{
      padding: 2rem 1.6rem 2.2rem;
      line-height: 1.7;
      font-size: 1.1rem;
    }}
    h1, h2, h3 {{
      font-family: "Palatino Linotype", Palatino, serif;
      color: #2b211c;
      margin-top: 1.4rem;
      margin-bottom: 0.5rem;
    }}
    h1 {{
      margin-top: 0;
      font-size: 2rem;
      border-bottom: 2px solid var(--frame);
      padding-bottom: 0.3rem;
    }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.2rem; }}
    p {{ margin: 0.8rem 0; }}
    ul {{
      margin-top: 0.6rem;
      margin-bottom: 0.8rem;
      padding-left: 1.2rem;
    }}
    li {{ margin: 0.3rem 0; }}
    .footer {{
      border-top: 1px solid var(--frame);
      font-size: 0.9rem;
      color: #5f5146;
      padding: 0.9rem 1.4rem;
      background: #f4ecde;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <div class="titlebar">story_gen publication</div>
    <article class="content">
{body_html}
    </article>
    <footer class="footer">Published with story_gen</footer>
  </main>
</body>
</html>
"""


def build_site(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Build `site/index.html` from the source markdown file."""
    markdown = input_path.read_text(encoding="utf-8")
    html_content = markdown_to_html(markdown)
    page = build_page(html_content)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    return output_path


def main() -> None:
    output_path = build_site()
    print(f"Built site page at {output_path}")


if __name__ == "__main__":
    main()
