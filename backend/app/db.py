"""Database engine, session and ORM models (PostgreSQL + pgvector)."""
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import EMBED_DIM, get_settings

engine = create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Classroom(Base):
    __tablename__ = "classrooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    teacher_token: Mapped[str] = mapped_column(String(64))
    current_scene: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lesson: Mapped["Lesson | None"] = relationship(back_populates="classroom", uselist=False,
                                                   cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), unique=True)
    topic: Mapped[str] = mapped_column(String(120))
    content: Mapped[dict] = mapped_column(JSON)  # validated LessonOut
    engine: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    classroom: Mapped[Classroom] = relationship(back_populates="lesson")


class NoteChunk(Base):
    """A slice of the teacher's notes plus its embedding, used for RAG ('ask your notes')."""
    __tablename__ = "note_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    student: Mapped[str] = mapped_column(String(40))
    scene: Mapped[int] = mapped_column(Integer)
    question: Mapped[int] = mapped_column(Integer)
    choice: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Doubt(Base):
    __tablename__ = "doubts"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    student: Mapped[str] = mapped_column(String(40))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
