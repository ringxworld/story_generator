from story_gen.site_builder import build_page, markdown_to_html


def test_markdown_to_html_converts_headers_and_lists() -> None:
    source = "# Title\n\n## Section\n\n- one\n- two\n\nBody text."
    html = markdown_to_html(source)
    assert "<h1>Title</h1>" in html
    assert "<h2>Section</h2>" in html
    assert "<ul>" in html
    assert "<li>one</li>" in html
    assert "<li>two</li>" in html
    assert "<p>Body text.</p>" in html


def test_build_page_wraps_content() -> None:
    body = "<h1>Story</h1>"
    page = build_page(body)
    assert "<title>story_gen | Story</title>" in page
    assert body in page
