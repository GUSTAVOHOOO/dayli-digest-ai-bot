from unittest.mock import MagicMock, patch

from src.collectors.blogs import BlogsCollector, _blog_sources
from src.utils.config_loader import load_config


def test_blog_sources_are_structured_with_category_and_authority():
    config = load_config("config/feeds.yaml")
    sources = _blog_sources(config)

    assert len(sources) >= 10
    assert all(source["url"] for source in sources)
    assert all(source["category"] for source in sources)
    assert all(source["authority"] for source in sources)


def test_invalid_blog_feed_is_ignored_with_log():
    response = MagicMock()
    response.text = "not rss"
    response.raise_for_status.return_value = None
    feed = MagicMock()
    feed.entries = []
    feed.bozo = True
    feed.bozo_exception = Exception("bad feed")

    collector = BlogsCollector()
    collector.SOURCES = [{
        "name": "Invalid",
        "url": "https://example.com/rss",
        "category": "test",
        "authority": "low",
        "inclusion_reason": "test",
    }]
    with patch("src.collectors.blogs.httpx.get", return_value=response), \
         patch("src.collectors.blogs.feedparser.parse", return_value=feed), \
         patch("src.collectors.blogs.log") as log:
        articles = collector.fetch()

    assert articles == []
    log.warning.assert_called()
