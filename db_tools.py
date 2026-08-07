"""Database tools for shared memory between VS Code assistant and Telegram bot."""

import os
import json
import psycopg2
from datetime import datetime

DB_HOST = os.getenv("DB_HOST", "postgres17")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "kabahome_memory")
DB_USER = os.getenv("DB_USER", "kabahome_bot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "kbmem2026@@")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )


def get_session_summary() -> str:
    """Get summary of current session: recent actions and pending items."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sessions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "Nenhuma sessao ativa encontrada."
        sess_id = row[0]

        result = []

        # Pendencias
        cur.execute(
            "SELECT category, description FROM actions WHERE session_id=%s AND status='pending' ORDER BY id",
            (sess_id,)
        )
        pendings = cur.fetchall()
        if pendings:
            result.append("=== PENDENCIAS ===")
            for cat, desc in pendings:
                result.append(f"[{cat}] {desc}")

        # Ultimas acoes concluidas
        cur.execute(
            "SELECT action_type, category, description FROM actions WHERE session_id=%s AND status='done' ORDER BY id DESC LIMIT 10",
            (sess_id,)
        )
        dones = cur.fetchall()
        if dones:
            result.append("\n=== ULTIMAS ACOES ===")
            for atype, cat, desc in dones:
                result.append(f"[{atype}/{cat}] {desc}")

        # Contexto atual
        cur.execute("SELECT key, value FROM context WHERE session_id=%s ORDER BY key", (sess_id,))
        ctxs = cur.fetchall()
        if ctxs:
            result.append("\n=== ESTADO ATUAL ===")
            for key, val in ctxs:
                result.append(f"{key}: {val}")

        return "\n".join(result)
    finally:
        cur.close()
        conn.close()


def add_action(action_type: str, category: str, description: str, status: str = "done", details: str = "") -> str:
    """Register a new action in the current session."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sessions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "Nenhuma sessao ativa."
        sess_id = row[0]

        cur.execute(
            "INSERT INTO actions (session_id, action_type, category, description, details, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (sess_id, action_type, category, description, details, status)
        )
        action_id = cur.fetchone()[0]
        conn.commit()
        return f"Acao #{action_id} registrada: [{status}] {description}"
    finally:
        cur.close()
        conn.close()


def get_pending() -> str:
    """List all pending items."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, category, description FROM actions WHERE status='pending' ORDER BY id")
        rows = cur.fetchall()
        if not rows:
            return "Nenhuma pendencia."
        result = ["=== PENDENCIAS ==="]
        for aid, cat, desc in rows:
            result.append(f"#{aid} [{cat}] {desc}")
        return "\n".join(result)
    finally:
        cur.close()
        conn.close()


def update_context(key: str, value: str) -> str:
    """Update or set a context key-value pair."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sessions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "Nenhuma sessao ativa."
        sess_id = row[0]

        cur.execute(
            "INSERT INTO context (session_id, key, value) VALUES (%s,%s,%s) ON CONFLICT (session_id, key) DO UPDATE SET value=%s, updated_at=NOW()",
            (sess_id, key, value, value)
        )
        conn.commit()
        return f"Contexto atualizado: {key} = {value}"
    finally:
        cur.close()
        conn.close()


def mark_done(action_id: int) -> str:
    """Mark a pending action as done."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE actions SET status='done' WHERE id=%s RETURNING description", (action_id,))
        row = cur.fetchone()
        if not row:
            return f"Acao #{action_id} nao encontrada."
        conn.commit()
        return f"Acao #{action_id} concluida: {row[0]}"
    finally:
        cur.close()
        conn.close()

