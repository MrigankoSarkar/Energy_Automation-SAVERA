from app.services.ai.gemini_service import GeminiService
from app.services.ai.prompt_manager import PromptManager


def test_gemini_qa_insufficient_data():
    gs = GeminiService(enabled=False)
    res = gs.ask("What happened to energy consumption yesterday?", context_data={})
    assert res["status"] == "insufficient_data"
    assert res["answer"] == "Insufficient data available."


def test_gemini_qa_top_meters():
    gs = GeminiService(enabled=False)
    context = {
        "meters": [
            {"meter_name": "M1", "value": 100.0},
            {"meter_name": "M2", "value": 500.0},
            {"meter_name": "M3", "value": 250.0},
        ]
    }
    res = gs.ask("Which meter consumed the most energy?", context_data=context)
    assert res["success"] is True
    assert "M2: 500.0 kWh" in res["answer"]
    assert "Top energy consuming meters:" in res["answer"]


def test_gemini_qa_total_energy():
    gs = GeminiService(enabled=False)
    context = {"total_energy": 9206.83}
    res = gs.ask("What was total consumption yesterday?", context_data=context)
    assert res["success"] is True
    assert "9206.83 kWh" in res["answer"]


def test_prompt_manager_rules():
    prompt = PromptManager.build_qa_prompt("Test question", {"metric": 123})
    assert "NEVER invent, assume, or hallucinate" in prompt
    assert "Insufficient data available." in prompt
    assert "Test question" in prompt
