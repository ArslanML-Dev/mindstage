"""Initial schema: classrooms, lessons, pgvector note chunks, answers, doubts.

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "classrooms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(8), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("teacher_token", sa.String(64), nullable=False),
        sa.Column("current_scene", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("classroom_id", sa.Integer, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), unique=True),
        sa.Column("topic", sa.String(120), nullable=False),
        sa.Column("content", sa.JSON, nullable=False),
        sa.Column("engine", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "note_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("classroom_id", sa.Integer, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), index=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
    )
    op.execute("CREATE INDEX ix_note_chunks_embedding ON note_chunks "
               "USING hnsw (embedding vector_cosine_ops)")
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("classroom_id", sa.Integer, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), index=True),
        sa.Column("student", sa.String(40), nullable=False),
        sa.Column("scene", sa.Integer, nullable=False),
        sa.Column("question", sa.Integer, nullable=False),
        sa.Column("choice", sa.Integer, nullable=False),
        sa.Column("correct", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "doubts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("classroom_id", sa.Integer, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), index=True),
        sa.Column("student", sa.String(40), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("sources", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    for table in ("doubts", "answers", "note_chunks", "lessons", "classrooms"):
        op.drop_table(table)
