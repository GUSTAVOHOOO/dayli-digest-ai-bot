from src.processors.papers_intelligence import analyze_paper_signals, apply_paper_intelligence
from src.processors.scorer import calculate_attention_score


def base_analysis():
    return {
        "technical_depth": 7,
        "novelty": 7,
        "momentum": 5,
        "community_adoption": 4,
        "authority": 4,
        "implementation_value": 5,
        "cross_source_validation": 0,
        "noise_risk": 2,
        "entities": [],
    }


def test_breakthrough_paper_with_code_and_benchmark_gets_boost():
    text = "OpenAI presents a breakthrough novel architecture with code on GitHub and benchmark results."

    paper = analyze_paper_signals(text)
    updated = apply_paper_intelligence(base_analysis(), paper)

    assert paper["paper_type"] == "breakthrough"
    assert paper["has_code"] is True
    assert paper["has_benchmark"] is True
    assert updated["authority"] >= 10.0
    assert updated["implementation_value"] > 5


def test_survey_is_lower_impact_than_breakthrough():
    survey = analyze_paper_signals("A survey and taxonomy of retrieval augmented generation methods from MIT.")
    breakthrough = analyze_paper_signals("A breakthrough model from MIT with code and benchmark results.")

    assert survey["paper_type"] == "survey"
    assert survey["paper_impact_score"] < breakthrough["paper_impact_score"]


def test_incremental_paper_reduces_score():
    paper = analyze_paper_signals("An incremental preliminary improvement with marginal gains.")
    analysis = base_analysis()
    updated = apply_paper_intelligence(analysis, paper)

    assert updated["novelty"] < analysis["novelty"]
    assert updated["noise_risk"] > analysis["noise_risk"]
    assert calculate_attention_score(updated).final_score < calculate_attention_score(analysis).final_score


def test_authority_institution_boost():
    paper = analyze_paper_signals("Stanford and Berkeley release a benchmark dataset for agent evaluation.")

    assert "stanford" in paper["authority_institutions"]
    assert "berkeley" in paper["authority_institutions"]
    assert paper["paper_authority"] == 8.5
