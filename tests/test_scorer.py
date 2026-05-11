import pytest
from src.processors.scorer import calculate_score, MIN_SCORE_THRESHOLD

def test_positive_keywords():
    """Tests if positive keywords correctly increase the score."""
    text = "This is a SOTA benchmark with GPT-5 breakthrough"
    score = calculate_score(text)
    # SOTA(+1), benchmark(+1), GPT-5(+1), breakthrough(+1) = 4.0
    assert score == 4.0

def test_neutral_keywords():
    """Tests if neutral keywords correctly increase the score."""
    text = "This is a demo review"
    score = calculate_score(text)
    # demo(+0.5), review(+0.5) = 1.0
    assert score == 1.0

def test_max_score():
    """Tests if the score is correctly capped at MAX_SCORE (5.0)."""
    text = "SOTA benchmark GPT-5 DeepSeek open source vulnerability breakthrough demo review opinion"
    score = calculate_score(text)
    assert score == 5.0

def test_empty_text():
    """Tests if empty or None text returns a score of 0.0."""
    assert calculate_score("") == 0.0
    assert calculate_score(None) == 0.0

def test_threshold():
    """Tests if the score behaves correctly relative to the MIN_SCORE_THRESHOLD."""
    text = "Just a simple demo"
    score = calculate_score(text)
    assert score == 0.5
    assert score < MIN_SCORE_THRESHOLD
