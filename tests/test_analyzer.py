import json
from unittest.mock import MagicMock, patch

from src.models.analysis import validate_analysis
from src.processors.analyzer import _extract_repo_metadata, analyze_content


def test_validate_analysis_complete_json():
    result = validate_analysis({
        'category': 'agent_ecosystem',
        'entities': ['MCP', 'Anthropic'],
        'summary': 'Resumo curto.',
        'technical_depth': 8.0,
        'novelty': 7.5,
        'momentum': 6.5,
        'community_adoption': 6.0,
        'authority': 9.0,
        'implementation_value': 8.0,
        'cross_source_validation': 5.0,
        'noise_risk': 1.0,
        'why_it_matters': 'Explicacao objetiva.',
        'worth_testing': True,
        'key_points': ['ponto 1', 'ponto 2'],
    })
    assert result['category'] == 'agent_ecosystem'
    assert result['entities'] == ['MCP', 'Anthropic']
    assert result['technical_depth'] == 8.0
    assert result['momentum'] == 6.5
    assert result['cross_source_validation'] == 5.0
    assert result['worth_testing'] is True


def test_validate_analysis_missing_fields_get_safe_fallbacks():
    result = validate_analysis({'summary': 'Only summary'})
    assert result['category'] == 'ai_engineering'
    assert result['entities'] == []
    assert result['summary'] == 'Only summary'
    assert result['technical_depth'] == 0.0
    assert result['momentum'] == 0.0
    assert result['noise_risk'] == 10.0
    assert result['worth_testing'] is False
    assert result['key_points'] == []


def test_validate_analysis_clamps_numeric_fields():
    result = validate_analysis({
        'technical_depth': 12,
        'novelty': -1,
        'authority': '9.5',
        'implementation_value': 100,
        'noise_risk': -20,
    })
    assert result['technical_depth'] == 10.0
    assert result['novelty'] == 0.0
    assert result['authority'] == 9.5
    assert result['implementation_value'] == 10.0
    assert result['noise_risk'] == 0.0


def test_validate_analysis_rejects_non_json_object():
    assert validate_analysis('not json') is None


def test_analyze_content_non_json_returns_none():
    response = MagicMock()
    response.json.return_value = {'response': 'not json'}
    response.raise_for_status.return_value = None
    with patch('src.processors.analyzer.httpx.post', return_value=response):
        result = analyze_content({
            'url': 'https://example.com',
            'title': 'Example',
            'source': 'blogs',
            'clean_text': 'Some content',
        })
    assert result is None


def test_analysis_json_is_serializable_after_validation():
    result = validate_analysis({
        'category': 'ai_engineering',
        'summary': 'Resumo',
        'technical_depth': 5,
        'novelty': 6,
        'authority': 7,
        'implementation_value': 8,
        'noise_risk': 1,
        'why_it_matters': 'Importa',
        'worth_testing': True,
        'key_points': ['a'],
    })
    encoded = json.dumps(result)
    assert json.loads(encoded)['implementation_value'] == 8.0


def test_repo_metadata_extraction_ignores_readme_braces():
    text = (
        'Repo metadata JSON: {"repo_score": 7.5, "github_velocity": {"repo_score": 7.5}}\n\n'
        'README:\nExample with {braces} in markdown.'
    )

    result = _extract_repo_metadata(text)

    assert result["repo_score"] == 7.5
    assert result["github_velocity"]["repo_score"] == 7.5
