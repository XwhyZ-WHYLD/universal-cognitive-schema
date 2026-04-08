import json
from stage1_mvp import apply_constraints, validate_output

def test_constraints_apply():
    profile = {
        "communication_style": "analytical",
        "verbosity": "concise"
    }
    prompt = "Explain AI simply"
    
    result = apply_constraints(prompt, profile)
    
    assert "analytical" in result.lower()

def test_validation_basic():
    output = "This is a concise analytical explanation."
    score = validate_output(output)
    
    assert isinstance(score, float)
    assert score >= 0
