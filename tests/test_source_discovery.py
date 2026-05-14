import os
import tempfile

import src.storage.sqlite as sqlite
from src.processors.source_discovery import discover_source_suggestions, enqueue_source_suggestions


def test_suggestion_from_github_org():
    suggestions = discover_source_suggestions({
        "url": "https://github.com/example/repo",
        "entities": [],
    })

    urls = {suggestion["source_url"] for suggestion in suggestions}
    assert "https://github.com/example" in urls
    assert all(suggestion["status"] == "pending" for suggestion in suggestions)


def test_source_suggestion_deduplicates_in_sqlite():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        first = enqueue_source_suggestions({"url": "https://github.com/example/repo", "entities": []})
        second = enqueue_source_suggestions({"url": "https://github.com/example/other", "entities": []})
        stored = sqlite.get_source_suggestion("https://github.com/example")
    sqlite.DB_PATH = original

    assert first
    assert second
    assert stored["status"] == "pending"
    assert stored["source_type"] == "github_org"


def test_company_entity_suggests_official_source():
    suggestions = discover_source_suggestions({
        "url": "https://example.com/post",
        "entities": [{"name": "OpenAI", "normalized_name": "openai", "type": "company"}],
    })

    assert any(suggestion["source_url"] == "https://openai.com/news/" for suggestion in suggestions)
