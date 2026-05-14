from src.processors.readme_intelligence import (
    apply_readme_intelligence,
    infer_readme_intelligence,
    validate_readme_intelligence,
)
from src.processors.scorer import calculate_attention_score


def test_real_tool_readme_gets_practical_value():
    readme = """
    # Agent Runtime
    Installation: pip install agent-runtime
    Quickstart: create a tool-calling agent with memory.
    Architecture: provider adapters, evaluation pipeline and plugin system.
    Usage: run the CLI against local and hosted models.
    """

    result = infer_readme_intelligence(readme, title="agent-runtime")

    assert result["practical_value"] >= 5.0
    assert result["wrapper_risk"] < 5.0
    assert result["documentation_quality"] >= 5.0


def test_superficial_wrapper_readme_penalizes_score_inputs():
    readme = "# GPT UI\nA simple ChatGPT wrapper around the OpenAI API."
    readme_result = infer_readme_intelligence(readme, title="gpt-ui")
    analysis = {
        "technical_depth": 7,
        "novelty": 7,
        "momentum": 7,
        "community_adoption": 7,
        "authority": 7,
        "implementation_value": 7,
        "noise_risk": 1,
    }

    updated = apply_readme_intelligence(analysis, readme_result)

    assert updated["wrapper_risk"] >= 7.0
    assert updated["noise_risk"] > analysis["noise_risk"]
    assert updated["novelty"] < analysis["novelty"]
    assert calculate_attention_score(updated).final_score < calculate_attention_score(analysis).final_score


def test_readme_absent_gets_safe_fallback():
    result = infer_readme_intelligence(None)

    assert result["maturity"] == "early"
    assert result["documentation_quality"] == 0.0


def test_invalid_readme_json_is_normalized():
    result = validate_readme_intelligence("not-json")

    assert result["category"] == "unknown"
    assert result["wrapper_risk"] == 5.0
