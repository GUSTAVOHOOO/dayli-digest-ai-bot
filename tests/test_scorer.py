import json
from unittest.mock import patch

from src.processors.scorer import (
    MIN_SCORE_THRESHOLD,
    calculate_attention_score,
    calculate_intelligent_score,
    classify_attention_tier,
    process_score,
)

def test_high_value_analysis_scores_high():
    analysis = {
        'author_authority': 'high',
        'content_type': 'breakthrough',
        'has_code': True,
        'complexity_level': 'expert',
        'technical_keywords': ['llm', 'benchmark', 'agents'],
    }

    assert calculate_intelligent_score(analysis) == 10.0

def test_medium_analysis_scores_partially():
    analysis = {
        'author_authority': 'medium',
        'content_type': 'educational',
        'has_code': False,
        'complexity_level': 'intermediate',
        'technical_keywords': ['transformer', 'rag'],
    }

    assert calculate_intelligent_score(analysis) == 5.4

def test_empty_analysis_stays_below_threshold():
    score = calculate_intelligent_score({})
    assert score == 0.0
    assert score < MIN_SCORE_THRESHOLD


def test_attention_score_high_signals_get_s_tier():
    result = calculate_attention_score({
        'technical_depth': 10,
        'novelty': 9,
        'momentum': 9,
        'community_adoption': 8,
        'authority': 10,
        'implementation_value': 9,
        'cross_source_validation': 7,
        'noise_risk': 1,
    })
    assert result.final_score == 9.0
    assert result.tier == 'S'
    assert result.passed is True
    assert result.score_breakdown['momentum'] == 9.0


def test_attention_score_penalizes_noise_risk():
    low_noise = calculate_attention_score({
        'technical_depth': 8,
        'novelty': 8,
        'momentum': 8,
        'community_adoption': 8,
        'authority': 8,
        'implementation_value': 8,
        'noise_risk': 1,
    })
    high_noise = calculate_attention_score({
        'technical_depth': 8,
        'novelty': 8,
        'momentum': 8,
        'community_adoption': 8,
        'authority': 8,
        'implementation_value': 8,
        'noise_risk': 9,
    })
    assert high_noise.final_score < low_noise.final_score
    assert high_noise.tier == 'C'


def test_attention_score_clamps_final_score():
    result = calculate_attention_score({
        'technical_depth': 99,
        'novelty': 99,
        'momentum': 99,
        'community_adoption': 99,
        'authority': 99,
        'implementation_value': 99,
        'noise_risk': -10,
    })
    assert result.final_score == 10.0


def test_attention_tier_classification_requires_low_noise_for_s():
    assert classify_attention_tier(9.5, noise_risk=1.0) == 'S'
    assert classify_attention_tier(9.5, noise_risk=5.0) == 'B'
    assert classify_attention_tier(7.6, noise_risk=3.0) == 'A'
    assert classify_attention_tier(5.6, noise_risk=5.0) == 'B'
    assert classify_attention_tier(5.6, noise_risk=8.0) == 'C'


def test_process_score_preserves_analysis_json_with_attention_breakdown():
    article = {
        'url': 'https://example.com',
        'source': 'blogs',
        'md5_hash': 'hash',
        'analysis_json': json.dumps({
            'technical_depth': 10,
            'novelty': 9,
            'momentum': 9,
            'community_adoption': 8,
            'authority': 10,
            'implementation_value': 9,
            'cross_source_validation': 7,
            'noise_risk': 1,
        }),
    }
    with patch('src.processors.summarizer.process_summarize.delay') as delay:
        result = process_score.run(article)

    updated = json.loads(article['analysis_json'])
    assert result['score'] == 9.0
    assert updated['tier'] == 'S'
    assert updated['score_breakdown']['community_adoption'] == 8.0
    delay.assert_called_once()


def test_attention_score_falls_back_to_legacy_schema():
    analysis = {
        'author_authority': 'medium',
        'content_type': 'educational',
        'has_code': False,
        'complexity_level': 'intermediate',
        'technical_keywords': ['transformer', 'rag'],
    }
    assert calculate_intelligent_score(analysis) == 5.4
