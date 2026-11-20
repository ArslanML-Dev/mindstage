import copy

import pytest
from pydantic import ValidationError

from app.ai import DEMO_LESSON, parse_lesson
from app.rag import chunk_text
from app.schemas import Lesson, is_safe_formula


def test_demo_lesson_is_valid():
    lesson = Lesson.model_validate(DEMO_LESSON)
    assert len(lesson.scenes) == 4
    assert {s.visual.type for s in lesson.scenes} == {"flowchart", "keyfacts", "slider", "chart"}


def test_parse_lesson_accepts_code_fenced_json():
    import json
    raw = "```json\n" + json.dumps(DEMO_LESSON) + "\n```"
    assert parse_lesson(raw).topic.startswith("Photosynthesis")


@pytest.mark.parametrize("formula,ok", [
    ("100*(1-Math.exp(-x/25))", True), ("Math.sin(x*Math.PI/180)*10", True),
    ("alert(1)", False), ("x; fetch('/')", False), ("", False)])
def test_formula_whitelist(formula, ok):
    assert is_safe_formula(formula) is ok


def test_unsafe_formula_rejects_lesson():
    bad = copy.deepcopy(DEMO_LESSON)
    bad["scenes"][2]["visual"]["formula"] = "window.location='//evil'"
    with pytest.raises(ValidationError):
        Lesson.model_validate(bad)


def test_chart_needs_matching_labels_and_values():
    bad = copy.deepcopy(DEMO_LESSON)
    bad["scenes"][3]["visual"]["values"] = [1, 2, 3]
    with pytest.raises(ValidationError):
        Lesson.model_validate(bad)


def test_flowchart_drops_edges_to_unknown_nodes():
    data = copy.deepcopy(DEMO_LESSON)
    data["scenes"][0]["visual"]["edges"].append({"from": "sun", "to": "ghost"})
    lesson = Lesson.model_validate(data)
    assert all(e.target != "ghost" for e in lesson.scenes[0].visual.edges)


def test_chunks_overlap():
    words = [f"w{i}" for i in range(300)]
    chunks = chunk_text(" ".join(words), size=120, overlap=30)
    assert len(chunks) == 3
    assert chunks[1].split()[0] == "w90"  # second window starts 90 words in
    assert chunks[-1].split()[-1] == "w299"


def test_retired_model_falls_back_and_errors_are_readable():
    import pytest
    from google.genai import errors
    from app import ai

    def gone(model):
        if model == "old-model":
            raise errors.APIError(404, {"error": {"code": 404, "message": "gone", "status": "NOT_FOUND"}})
        return f"ok:{model}"

    assert ai._call(["old-model", "new-model"], gone) == ("ok:new-model", "new-model")

    def limited(model):
        raise errors.APIError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})

    with pytest.raises(ai.AIError, match="rate limit"):
        ai._call(["m"], limited)
