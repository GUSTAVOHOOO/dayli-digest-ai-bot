import json

from src.processors.entities import entities_to_dicts, extract_entities


def test_alias_mcp_and_model_context_protocol_are_normalized():
    entities = extract_entities(
        title='MCP support for agents',
        text='Model Context Protocol tools are included.',
    )
    normalized = [entity.normalized_name for entity in entities]
    assert normalized.count('model context protocol') == 1
    assert entities[0].to_dict()


def test_github_repo_is_detected_from_url():
    entities = extract_entities(url='https://github.com/openai/codex/releases/tag/v1')
    assert entities[0].type == 'github_repo'
    assert entities[0].normalized_name == 'openai/codex'


def test_entities_from_llm_are_normalized():
    entities = extract_entities(analysis={'entities': ['MCP', {'name': 'Anthropic', 'type': 'company'}]})
    assert {entity.normalized_name for entity in entities} == {'model context protocol', 'anthropic'}


def test_entities_are_deduplicated_and_json_serializable():
    entities = extract_entities(title='MCP', text='Model Context Protocol MCP')
    encoded = json.dumps(entities_to_dicts(entities))
    decoded = json.loads(encoded)
    assert len(decoded) == 1
    assert decoded[0]['type'] == 'protocol'
