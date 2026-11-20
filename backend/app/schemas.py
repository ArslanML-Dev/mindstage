"""Pydantic schemas. The LLM's lesson JSON must pass `Lesson` before anything reaches the classroom."""
import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Short = Annotated[str, Field(min_length=1, max_length=160)]


class FlowNode(BaseModel):
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_]{1,24}$")]
    label: Annotated[str, Field(min_length=1, max_length=40)]


class FlowEdge(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    label: Annotated[str, Field(max_length=25)] = ""
    model_config = {"populate_by_name": True}


class FlowchartVisual(BaseModel):
    type: Literal["flowchart"]
    nodes: Annotated[list[FlowNode], Field(min_length=2, max_length=8)]
    edges: Annotated[list[FlowEdge], Field(max_length=12)] = []

    @model_validator(mode="after")
    def edges_point_to_nodes(self):
        ids = {n.id for n in self.nodes}
        self.edges = [e for e in self.edges if e.source in ids and e.target in ids]
        return self


class ChartVisual(BaseModel):
    type: Literal["chart"]
    chart_type: Literal["bar", "line"] = "bar"
    title: Annotated[str, Field(max_length=60)] = ""
    labels: Annotated[list[Annotated[str, Field(max_length=24)]], Field(min_length=2, max_length=8)]
    values: Annotated[list[float], Field(min_length=2, max_length=8)]
    unit: Annotated[str, Field(max_length=16)] = ""

    @model_validator(mode="after")
    def same_length(self):
        if len(self.labels) != len(self.values):
            raise ValueError("labels and values must have the same length")
        return self


class Fact(BaseModel):
    emoji: Annotated[str, Field(max_length=4)] = "•"
    text: Annotated[str, Field(min_length=1, max_length=90)]


class KeyFactsVisual(BaseModel):
    type: Literal["keyfacts"]
    facts: Annotated[list[Fact], Field(min_length=2, max_length=5)]


_FORMULA_TOKEN = re.compile(r"\s*(Math\.(?:sin|cos|tan|sqrt|pow|PI|abs|log|exp)|x|\d+(?:\.\d+)?|[+\-*/(),])")


def is_safe_formula(formula: str) -> bool:
    """Only x, numbers, arithmetic and a few Math functions: the browser evaluates this."""
    if not formula or len(formula) > 120:
        return False
    pos = 0
    while pos < len(formula):
        m = _FORMULA_TOKEN.match(formula, pos)
        if not m:
            return False
        pos = m.end()
    return True


class SliderVisual(BaseModel):
    type: Literal["slider"]
    label: Annotated[str, Field(max_length=40)]
    unit: Annotated[str, Field(max_length=10)] = ""
    min: float = 0
    max: float = 100
    value: float = 50
    formula: str
    result_label: Annotated[str, Field(max_length=40)]
    result_unit: Annotated[str, Field(max_length=10)] = ""

    @field_validator("formula")
    @classmethod
    def formula_is_safe(cls, v: str) -> str:
        if not is_safe_formula(v):
            raise ValueError(f"unsafe formula: {v!r}")
        return v

    @model_validator(mode="after")
    def range_ok(self):
        if self.max <= self.min:
            raise ValueError("max must be greater than min")
        self.value = min(max(self.value, self.min), self.max)
        return self


Visual = Annotated[FlowchartVisual | ChartVisual | KeyFactsVisual | SliderVisual, Field(discriminator="type")]


class MCQ(BaseModel):
    question: Short
    options: Annotated[list[Annotated[str, Field(min_length=1, max_length=80)]], Field(min_length=4, max_length=4)]
    answer_index: Annotated[int, Field(ge=0, le=3)]
    why: Annotated[str, Field(max_length=160)] = ""


class Scene(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=60)]
    story: Annotated[str, Field(min_length=1, max_length=450)]
    analogy: Annotated[str, Field(max_length=200)] = ""
    visual: Visual
    mcqs: Annotated[list[MCQ], Field(min_length=1, max_length=2)]


class Lesson(BaseModel):
    topic: Annotated[str, Field(min_length=1, max_length=80)]
    scenes: Annotated[list[Scene], Field(min_length=2, max_length=6)]
    summary_notes: Annotated[list[Annotated[str, Field(max_length=200)]], Field(min_length=3, max_length=8)]


# ---------- API payloads ----------

class ClassroomCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)] = "My class"


class ClassroomCreated(BaseModel):
    code: str
    title: str
    teacher_token: str


class ClassroomInfo(BaseModel):
    code: str
    title: str
    current_scene: int
    has_lesson: bool


class LessonOut(BaseModel):
    code: str
    engine: str
    lesson: Lesson
    chunks_indexed: int = 0


class AskIn(BaseModel):
    student: Annotated[str, Field(min_length=1, max_length=40)]
    question: Annotated[str, Field(min_length=3, max_length=500)]


class Source(BaseModel):
    position: int
    text: str
    score: float


class AskOut(BaseModel):
    answer: str
    sources: list[Source]
