"""Renderer (FR-010 / SC-006; research.md D6 row 14): standalone HTML artifact
mirroring the grouped structure — title, source link, sections in document
order, inline text + belonging images, visible fallback markers."""

from agentic_rag_mcp.search.web.research import render_page

SECTIONS = [
    {"heading": "Trace a message",
     "blocks": [
         {"type": "p", "text": "In the Exchange admin center, open message trace."},
         {"type": "img", "src": "https://docs.example/img/trace-step1.png"},
     ]},
    {"heading": "Understand the results",
     "blocks": [{"type": "p", "text": "Each row expands to show the full event chain."}]},
]


def test_render_mirrors_grouped_structure_in_order():
    html = render_page(SECTIONS, "https://docs.example/guide", "Message Trace Guide")
    assert html.startswith("<!DOCTYPE html>")                     # standalone artifact
    assert "<title>Message Trace Guide</title>" in html
    assert 'href="https://docs.example/guide"' in html            # source link
    assert html.index("Trace a message") < html.index("In the Exchange admin center") \
        < html.index("trace-step1.png") < html.index("Understand the results") \
        < html.index("Each row expands")                          # document order (FR-010)
    assert "<img" in html and "loading=" in html                   # inline images, lazy


def test_render_fallback_shows_snippet_with_visible_marker():
    html = render_page([], "https://docs.example/x", "Some Page",
                       fallback_snippet="the search snippet text")
    assert "the search snippet text" in html
    assert "fallback" in html.lower()                              # visible marker (contract inv. 2)


def test_render_fallback_default_marker_when_no_snippet():
    html = render_page([], "https://docs.example/x", "P", fallback_snippet=None)
    assert "no content" in html.lower()                            # honest, never blank
