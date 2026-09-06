"""Simple Postgres helpers for interaction logging."""
from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)


def _get_conn():
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


def ensure_table():
    sql = """
    CREATE TABLE IF NOT EXISTS interactions (
      id SERIAL PRIMARY KEY,
      timestamp TIMESTAMP DEFAULT NOW(),
      question TEXT,
      answer TEXT,
      retrieval_method TEXT,
      prompt_variant TEXT,
      response_time_ms INT,
      sources JSONB,
      feedback SMALLINT
    );
    """
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


def log_interaction(question: str, answer: str, retrieval_method: str | None = None, prompt_variant: str | None = None, response_time_ms: int | None = None, sources: Any | None = None) -> int:
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO interactions (question, answer, retrieval_method, prompt_variant, response_time_ms, sources) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                    (question, answer, retrieval_method, prompt_variant, response_time_ms, Json(sources or [])),
                )
                new_id = cur.fetchone()[0]
                return int(new_id)
    finally:
        conn.close()


def update_feedback(interaction_id: int, feedback: int) -> None:
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE interactions SET feedback = %s WHERE id = %s", (int(feedback), int(interaction_id)))
    finally:
        conn.close()
