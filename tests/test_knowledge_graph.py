import os
import tempfile

import src.storage.sqlite as sqlite
from src.processors.knowledge_graph import (
    has_entity_appeared,
    novelty_score_for_entities,
    record_item_entities,
    related_entities_for_topic,
)
from src.storage.sqlite import save_knowledge_relation, upsert_knowledge_entity


def test_knowledge_entity_insert_is_idempotent():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        first = upsert_knowledge_entity({"name": "MCP", "normalized_name": "mcp", "type": "protocol"})
        second = upsert_knowledge_entity({"name": "MCP", "normalized_name": "mcp", "type": "protocol"})
        history = sqlite.get_entity_history("mcp", "protocol")
    sqlite.DB_PATH = original

    assert first == second
    assert len(history) == 1


def test_entity_cluster_relation_can_be_queried():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        entity_id = upsert_knowledge_entity({"name": "LangChain", "normalized_name": "langchain", "type": "framework"})
        save_knowledge_relation(entity_id, "belongs_to_cluster", "cluster-1", "cluster")
        related = related_entities_for_topic("cluster-1")
    sqlite.DB_PATH = original

    assert related[0]["normalized_name"] == "langchain"


def test_novelty_detection_uses_history():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        record_item_entities(
            {"url": "https://example.com"},
            [{"name": "Claude", "normalized_name": "claude", "type": "model"}],
        )
        seen = has_entity_appeared("claude", "model")
        novelty = novelty_score_for_entities([
            {"name": "Claude", "normalized_name": "claude", "type": "model"},
            {"name": "NewThing", "normalized_name": "newthing", "type": "concept"},
        ])
    sqlite.DB_PATH = original

    assert seen is True
    assert novelty == 5.0
