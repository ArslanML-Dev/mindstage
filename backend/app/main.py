"""MindStage API — FastAPI service for classrooms, AI lessons, RAG doubts and live sync."""
import secrets
import string

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from . import ai, rag
from .config import get_settings
from .db import Answer, Classroom, Doubt, Lesson, SessionLocal, get_db
from .live import hub
from .notes import NotesError, extract_text
from .schemas import (AskIn, AskOut, ClassroomCreate, ClassroomCreated, ClassroomInfo, LessonOut, Source)
from .schemas import Lesson as LessonSchema

app = FastAPI(title="MindStage API", version="1.0.0",
              description="AI classroom: notes → cinematic lessons, live sync, and RAG answers from the notes.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])

CODE_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def get_classroom(code: str, db: Session) -> Classroom:
    room = db.scalar(select(Classroom).where(Classroom.code == code.upper()))
    if not room:
        raise HTTPException(404, "No class with that code.")
    return room


def require_teacher(room: Classroom, token: str | None):
    if not token or not secrets.compare_digest(token, room.teacher_token):
        raise HTTPException(403, "Only the teacher can do this.")


@app.get("/api/health")
def health():
    return {"status": "ok", "ai": "gemini" if get_settings().ai_enabled else "demo"}


@app.post("/api/classrooms", response_model=ClassroomCreated, status_code=201)
def create_classroom(body: ClassroomCreate, db: Session = Depends(get_db)):
    while True:
        code = new_code()
        if not db.scalar(select(Classroom.id).where(Classroom.code == code)):
            break
    room = Classroom(code=code, title=body.title.strip(), teacher_token=secrets.token_urlsafe(32))
    db.add(room)
    db.commit()
    return ClassroomCreated(code=room.code, title=room.title, teacher_token=room.teacher_token)


@app.get("/api/classrooms/{code}", response_model=ClassroomInfo)
def classroom_info(code: str, db: Session = Depends(get_db)):
    room = get_classroom(code, db)
    return ClassroomInfo(code=room.code, title=room.title, current_scene=room.current_scene,
                         has_lesson=room.lesson is not None)


@app.post("/api/classrooms/{code}/lesson", response_model=LessonOut)
def create_lesson(code: str, notes: str = Form(""), file: UploadFile | None = File(None),
                  x_teacher_token: str | None = Header(None), db: Session = Depends(get_db)):
    room = get_classroom(code, db)
    require_teacher(room, x_teacher_token)
    text = notes.strip()
    try:
        if file is not None and file.filename:
            text = (text + "\n\n" + extract_text(file.filename, file.file.read())).strip()
        if len(text) < 40:
            raise HTTPException(422, "Add at least a few sentences of notes (or upload a file).")
        lesson, engine = ai.generate_lesson(text)
        chunks = rag.index_notes(db, room.id, text)
    except (NotesError, ai.AIError) as e:
        raise HTTPException(422, str(e)) from e
    if room.lesson:
        db.delete(room.lesson)
        db.flush()
    db.add(Lesson(classroom_id=room.id, topic=lesson.topic, content=lesson.model_dump(by_alias=True), engine=engine))
    room.current_scene = 0
    db.commit()
    return LessonOut(code=room.code, engine=engine, lesson=lesson, chunks_indexed=chunks)


@app.get("/api/classrooms/{code}/lesson", response_model=LessonOut)
def get_lesson(code: str, db: Session = Depends(get_db)):
    room = get_classroom(code, db)
    if not room.lesson:
        raise HTTPException(404, "The teacher hasn't started a lesson yet.")
    return LessonOut(code=room.code, engine=room.lesson.engine,
                     lesson=LessonSchema.model_validate(room.lesson.content))


@app.post("/api/classrooms/{code}/ask", response_model=AskOut)
async def ask(code: str, body: AskIn):
    def work():
        with SessionLocal() as db:
            room = get_classroom(code, db)
            hits = rag.search(db, room.id, body.question)
            text = ai.answer(body.question, [c.text for c, _ in hits])
            sources = [Source(position=c.position, text=c.text[:300], score=s) for c, s in hits]
            db.add(Doubt(classroom_id=room.id, student=body.student, question=body.question, answer=text,
                         sources=[s.model_dump() for s in sources]))
            db.commit()
            return room.code, AskOut(answer=text, sources=sources)

    room_code, out = await run_in_threadpool(work)
    await hub.to_teachers(room_code, {"type": "doubt", "student": body.student, "question": body.question,
                                      "answer": out.answer})
    return out


@app.get("/api/classrooms/{code}/report")
def report(code: str, x_teacher_token: str | None = Header(None), db: Session = Depends(get_db)):
    room = get_classroom(code, db)
    require_teacher(room, x_teacher_token)
    rows = db.execute(select(Answer.student, func.count(), func.sum(case((Answer.correct, 1), else_=0)))
                      .where(Answer.classroom_id == room.id).group_by(Answer.student)).all()
    doubts = db.scalars(select(Doubt).where(Doubt.classroom_id == room.id).order_by(Doubt.created_at)).all()
    return {"students": [{"name": n, "answered": a, "correct": int(c or 0)} for n, a, c in rows],
            "doubts": [{"student": d.student, "question": d.question, "answer": d.answer} for d in doubts]}


def _scene_stats(db: Session, room_id: int, scene: int, question: int) -> dict:
    rows = db.execute(select(Answer.choice, func.count()).where(
        Answer.classroom_id == room_id, Answer.scene == scene, Answer.question == question)
        .group_by(Answer.choice)).all()
    counts = [0, 0, 0, 0]
    for choice, n in rows:
        counts[choice] = n
    return {"type": "stats", "scene": scene, "question": question, "counts": counts}


@app.websocket("/ws/{code}")
async def live(ws: WebSocket, code: str, role: str = "student", name: str = "Student", token: str = ""):
    code = code.upper()
    with SessionLocal() as db:
        room = db.scalar(select(Classroom).where(Classroom.code == code))
        if not room or (role == "teacher" and not secrets.compare_digest(token, room.teacher_token)):
            await ws.close(code=4403)
            return
        room_id, current = room.id, room.current_scene
    await ws.accept()
    await ws.send_json({"type": "scene", "index": current})
    await hub.join(code, ws, role, name[:40])
    try:
        while True:
            msg = await ws.receive_json()
            if role == "teacher" and msg.get("type") == "goto":
                index = int(msg.get("index", 0))
                with SessionLocal() as db:
                    db.get(Classroom, room_id).current_scene = index
                    db.commit()
                await hub.to_all(code, {"type": "scene", "index": index})
            elif role == "student" and msg.get("type") == "answer":
                scene, question, choice = int(msg["scene"]), int(msg["question"]), int(msg["choice"])
                with SessionLocal() as db:
                    lesson = LessonSchema.model_validate(db.get(Classroom, room_id).lesson.content)
                    correct = lesson.scenes[scene].mcqs[question].answer_index == choice
                    db.add(Answer(classroom_id=room_id, student=name[:40], scene=scene, question=question,
                                  choice=choice, correct=correct))
                    db.commit()
                    stats = _scene_stats(db, room_id, scene, question)
                await ws.send_json({"type": "answer_result", "scene": scene, "question": question,
                                    "correct": correct})
                await hub.to_teachers(code, stats)
    except (WebSocketDisconnect, KeyError, ValueError, IndexError, AttributeError):
        pass
    finally:
        await hub.leave(code, ws)
