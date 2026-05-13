import pytest
from src.processors.scorer import calculate_intelligent_score, MIN_SCORE_THRESHOLD

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
