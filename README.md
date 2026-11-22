# MindStage

**An AI classroom that turns a teacher's notes into a live, visual lesson.**

**Live:** https://mindstage-ai.vercel.app

A teacher uploads notes (PDF, Word, text, or a photo). Gemini turns them into a short lesson of scenes, each with a story, an analogy, an interactive visual (flowchart, chart, slider or key facts) and checkpoint questions. Students join with a 6-letter code and follow the teacher's screen live over WebSockets. Their answers come back to the teacher as a live chart, and their doubts are answered only from the teacher's own notes (RAG with pgvector), with the source passages shown.

## Why this matters

I built MindStage because I lived the problem as a student: the classroom has barely changed in a century. One teacher talks, a board fills up, and students spend the class copying instead of understanding.

The research is clear that this format costs students:

- A meta-analysis of **225 studies** of undergraduate STEM teaching found that students in traditional lecture courses were **1.5 times more likely to fail** than students in courses with active learning (average failure rate **34% vs 22%**), and exam scores improved by about **6%** with active learning. ([Freeman et al., *PNAS*, 2014](https://doi.org/10.1073/pnas.1319030111))

MindStage turns any lecture into active learning without asking teachers to redesign their course: their own notes become visual scenes, live checkpoint questions and a doubt-solver grounded in those notes, and the teacher sees in real time who understood.

## Architecture

```
 Next.js 16 (Vercel)                FastAPI (Docker on Render)              PostgreSQL 16 + pgvector
 ───────────────────                ──────────────────────────              ────────────────────────
 /teach  teacher console  ──REST──▶ POST /classrooms/{code}/lesson  ──▶ Gemini 3.8 Flash → validated JSON lesson
                                     │ chunk notes → Gemini embeddings ──▶ note_chunks (vector(768), HNSW)
 /class  student view     ──REST──▶ POST /classrooms/{code}/ask    ──▶ top-4 cosine search → grounded answer
         ▲     │                     │
         └─WS──┴──────────────────▶ /ws/{code}  scene sync · answers · live stats · presence · doubts
```

| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, WebSockets, Pydantic v2, SQLAlchemy 2, Alembic |
| Data | PostgreSQL 16 + pgvector (HNSW cosine index) |
| AI | Google Gemini (`gemini-3.8-flash`, `gemini-embedding-001` at 768 dims) |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4 |
| DevOps | Docker, GitHub Actions CI (pytest against a real pgvector service, Docker build, Next build) |

Every lesson the model returns is validated against a strict schema (scene count, MCQ shape, chart lengths, a whitelist for slider formulas) and retried up to 3 times. Without a `GEMINI_API_KEY` the app runs in **demo mode** with a built-in lesson and hash embeddings, so it works end to end anywhere.

## Run locally

```bash
docker run -d --name pg -e POSTGRES_PASSWORD=pg -p 5432:5432 pgvector/pgvector:pg16

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # set DATABASE_URL, optionally GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload # http://localhost:8000/docs
pytest                        # 19 tests

cd ../frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

## Deploy

- **Backend + database:** Render Blueprint (`render.yaml`) creates the Postgres database and the Docker web service. Add `GEMINI_API_KEY` in the Render dashboard.
- **Frontend:** Vercel, root directory `frontend`, env `NEXT_PUBLIC_API_URL=<Render URL>`.
- Set `CORS_ORIGINS` on Render to the Vercel URL.

## Roadmap

Voice narration, teacher accounts, lesson history and analytics, AWS deployment.
