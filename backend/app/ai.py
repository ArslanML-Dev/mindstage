"""The only module that talks to the LLM (Google Gemini).

Every model output is validated with Pydantic before use; invalid JSON is retried.
Without GEMINI_API_KEY the app runs in a clearly labelled demo mode (fixed lesson,
hash-based embeddings), so it can be deployed and tested before a key is added.
"""
import hashlib
import json
import math
import re

from pydantic import ValidationError

from .config import EMBED_DIM, get_settings
from .schemas import Lesson

MAX_TRIES = 3

LESSON_PROMPT = """You are MindStage, an AI that turns a teacher's notes into a short cinematic lesson
for a classroom screen. Students should feel they are watching a story, not reading notes.

Teacher notes:
\"\"\"{notes}\"\"\"

Return ONLY JSON with this exact shape:
{{
 "topic": "short topic name",
 "summary_notes": ["3-8 crisp revision points a student can study from, max 200 chars each"],
 "scenes": [  // 4 or 5 scenes that teach the notes in order
  {{
   "title": "max 7 words, like a movie chapter",
   "story": "max 60 words, simple story-style explanation for a 15-year-old",
   "analogy": "one everyday analogy, max 25 words",
   "visual": ONE of:
     {{"type":"flowchart","nodes":[{{"id":"a","label":"max 40 chars"}}],"edges":[{{"from":"a","to":"b","label":""}}]}}  (3-7 nodes),
     {{"type":"chart","chart_type":"bar"|"line","title":"","labels":["..."],"values":[numbers],"unit":""}}  (3-8 points, realistic),
     {{"type":"keyfacts","facts":[{{"emoji":"one emoji","text":"max 12 words"}}]}}  (3-5 facts),
     {{"type":"slider","label":"what x is","unit":"","min":0,"max":100,"value":50,
       "formula":"expression using only x, numbers, + - * / ( ) and Math.sin Math.cos Math.tan Math.sqrt Math.pow Math.PI Math.abs Math.log Math.exp",
       "result_label":"what the formula computes","result_unit":""}},
   "mcqs": [{{"question":"","options":["A","B","C","D"],"answer_index":0,"why":"one line"}}]  // exactly 2
  }}
 ]
}}
Use at least 3 different visual types across the scenes. Every fact must come from the notes.
"""

TRANSCRIBE_PROMPT = ("Transcribe all the teaching content in this file (printed or handwritten notes) "
                     "into clean plain text. Keep headings, definitions, formulas and lists. "
                     "Return only the text.")

ANSWER_PROMPT = """You are a teaching assistant answering a student's doubt during class.
Answer ONLY from the numbered note excerpts below. If they do not contain the answer, say
"Your teacher's notes don't cover this yet — ask your teacher." Keep it under 90 words and cite
excerpts like [1] or [2].

Note excerpts:
{context}

Student's question: {question}
"""


class AIError(Exception):
    pass


def _client():
    from google import genai
    return genai.Client(api_key=get_settings().gemini_api_key)


def _strip_fences(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def parse_lesson(raw_text: str) -> Lesson:
    """Parse + validate model output. Raises ValueError/ValidationError on bad output."""
    return Lesson.model_validate(json.loads(_strip_fences(raw_text)))


def generate_lesson(notes: str) -> tuple[Lesson, str]:
    s = get_settings()
    if not s.ai_enabled:
        return Lesson.model_validate(DEMO_LESSON), "demo"
    from google.genai import types

    client, last_error = _client(), None
    prompt = LESSON_PROMPT.format(notes=notes[:15000])
    for _ in range(MAX_TRIES):
        try:
            resp = client.models.generate_content(
                model=s.gemini_model, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6))
            return parse_lesson(resp.text), s.gemini_model
        except (ValidationError, ValueError, TypeError) as e:
            last_error = e
    raise AIError(f"The AI could not produce a valid lesson after {MAX_TRIES} tries: {last_error}")


def transcribe(data: bytes, mime: str) -> str:
    """Read a scanned PDF or a photo of notes into text, so it can be taught AND indexed for RAG."""
    s = get_settings()
    if not s.ai_enabled:
        raise AIError("Reading photos and scanned PDFs needs GEMINI_API_KEY. Upload text, Word or a text PDF.")
    from google.genai import types
    resp = _client().models.generate_content(
        model=s.gemini_model, contents=[TRANSCRIBE_PROMPT, types.Part.from_bytes(data=data, mime_type=mime)])
    return (resp.text or "").strip()


def _hash_embed(text: str) -> list[float]:
    """Demo-mode embedding: deterministic bag-of-words hashing, L2-normalised."""
    vec = [0.0] * EMBED_DIM
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vec[h % EMBED_DIM] += 1.0 if (h >> 8) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    s = get_settings()
    if not s.ai_enabled:
        return [_hash_embed(t) for t in texts]
    from google.genai import types
    out: list[list[float]] = []
    for i in range(0, len(texts), 50):
        resp = _client().models.embed_content(
            model=s.gemini_embed_model, contents=texts[i:i + 50],
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=EMBED_DIM))
        for e in resp.embeddings:
            norm = math.sqrt(sum(v * v for v in e.values)) or 1.0  # truncated dims need re-normalising
            out.append([v / norm for v in e.values])
    return out


def answer(question: str, excerpts: list[str]) -> str:
    if not excerpts:
        return "Your teacher hasn't shared notes for this class yet."
    s = get_settings()
    if not s.ai_enabled:
        return f"(Demo mode — no AI key.) The most relevant part of the notes says: “{excerpts[0][:300]}” [1]"
    context = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(excerpts))
    resp = _client().models.generate_content(
        model=s.gemini_model, contents=ANSWER_PROMPT.format(context=context, question=question))
    return (resp.text or "").strip()


DEMO_LESSON = {
    "topic": "Photosynthesis (demo lesson)",
    "summary_notes": [
        "Photosynthesis: plants use sunlight, water and CO2 to make glucose and release oxygen.",
        "It happens in chloroplasts, where chlorophyll captures light energy.",
        "Rate rises with light intensity until another factor (like CO2) becomes limiting.",
        "Plants start almost every food chain and produce much of Earth's oxygen.",
    ],
    "scenes": [
        {"title": "The Leaf Kitchen Opens",
         "story": "Every green leaf is a tiny kitchen. It takes in sunlight, water from the roots and carbon "
                  "dioxide from the air, then cooks its own food called glucose. Oxygen is the leftover it "
                  "releases for us to breathe.",
         "analogy": "A solar-powered kitchen that cooks sugar and gives away fresh air.",
         "visual": {"type": "flowchart",
                    "nodes": [{"id": "sun", "label": "Sunlight"}, {"id": "water", "label": "Water"},
                              {"id": "co2", "label": "CO2"}, {"id": "leaf", "label": "Chloroplast"},
                              {"id": "glu", "label": "Glucose"}, {"id": "o2", "label": "Oxygen"}],
                    "edges": [{"from": "sun", "to": "leaf", "label": "energy"}, {"from": "water", "to": "leaf"},
                              {"from": "co2", "to": "leaf"}, {"from": "leaf", "to": "glu", "label": "food"},
                              {"from": "leaf", "to": "o2", "label": "released"}]},
         "mcqs": [{"question": "What does a leaf make during photosynthesis?",
                   "options": ["Protein", "Glucose", "Salt", "Fat"], "answer_index": 1,
                   "why": "Glucose is the sugar the plant makes."},
                  {"question": "Which gas does the plant release?",
                   "options": ["Carbon dioxide", "Nitrogen", "Oxygen", "Helium"], "answer_index": 2,
                   "why": "Oxygen is released as a by-product."}]},
        {"title": "Green Solar Panels Inside",
         "story": "Inside leaf cells are chloroplasts full of chlorophyll, a green pigment. Chlorophyll catches "
                  "light energy like a solar panel, and that energy powers the whole food-making process.",
         "analogy": "Chlorophyll is the solar panel; the chloroplast is the factory around it.",
         "visual": {"type": "keyfacts",
                    "facts": [{"emoji": "🌿", "text": "Chlorophyll makes leaves green"},
                              {"emoji": "☀️", "text": "It absorbs red and blue light best"},
                              {"emoji": "🏭", "text": "Chloroplasts are the food factories"}]},
         "mcqs": [{"question": "Which pigment captures light?",
                   "options": ["Melanin", "Chlorophyll", "Haemoglobin", "Keratin"], "answer_index": 1,
                   "why": "Chlorophyll absorbs light energy."},
                  {"question": "Where does photosynthesis happen?",
                   "options": ["Nucleus", "Mitochondria", "Chloroplast", "Cell wall"], "answer_index": 2,
                   "why": "Chloroplasts are the site of photosynthesis."}]},
        {"title": "More Light, Faster Cooking",
         "story": "Brighter light speeds photosynthesis up — until the plant hits a limit. After that, more light "
                  "does not help, because something else like carbon dioxide becomes the bottleneck.",
         "analogy": "More cooks help until the kitchen runs out of ingredients.",
         "visual": {"type": "slider", "label": "Light intensity", "unit": "%", "min": 0, "max": 100,
                    "value": 40, "formula": "100*(1-Math.exp(-x/25))",
                    "result_label": "Photosynthesis rate", "result_unit": "%"},
         "mcqs": [{"question": "What happens to the rate after the limit?",
                   "options": ["Keeps rising", "Levels off", "Drops to zero", "Doubles"], "answer_index": 1,
                   "why": "Another factor limits it."},
                  {"question": "Which can become the limiting factor?",
                   "options": ["Carbon dioxide", "Soil colour", "Leaf shape", "Moonlight"], "answer_index": 0,
                   "why": "Low CO2 limits the rate even in bright light."}]},
        {"title": "Why Earth Needs Leaves",
         "story": "Plants feed almost every food chain and refresh the air we breathe. Ocean algae and land "
                  "plants together produce the oxygen that keeps us alive.",
         "analogy": "Plants are Earth's lungs and its first restaurant.",
         "visual": {"type": "chart", "chart_type": "bar", "title": "Approx. share of Earth's oxygen",
                    "labels": ["Ocean algae", "Land plants"], "values": [50, 50], "unit": "%"},
         "mcqs": [{"question": "Who starts almost every food chain?",
                   "options": ["Lions", "Plants", "Fungi", "Rocks"], "answer_index": 1,
                   "why": "Plants are producers."},
                  {"question": "Which group makes about half of Earth's oxygen?",
                   "options": ["Ocean algae", "Cars", "Volcanoes", "Clouds"], "answer_index": 0,
                   "why": "Ocean algae photosynthesise at huge scale."}]},
    ],
}
