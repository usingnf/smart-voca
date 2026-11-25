#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 클로드 스마트 보카 - SQLite 연결, 트랜잭션, 테이블 만들기 (계정·단어·이력·상태·옵션 저장소의 기반)
# 파일 위치: src/database.py

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH

# 테이블은 처음 연결할 때 한 번만 만든다 (IF NOT EXISTS라서 여러 번 실행해도 안전하다).
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_key TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    password_hash TEXT,
    is_public INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_state (
    user_key TEXT PRIMARY KEY REFERENCES users(user_key) ON DELETE CASCADE,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS custom_words (
    user_key TEXT NOT NULL REFERENCES users(user_key) ON DELETE CASCADE,
    word TEXT NOT NULL,
    pos TEXT NOT NULL,
    meanings_json TEXT NOT NULL,
    english_gloss TEXT NOT NULL DEFAULT '',
    synonyms_json TEXT NOT NULL DEFAULT '[]',
    example TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    license TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_key, word)
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_key TEXT NOT NULL REFERENCES users(user_key) ON DELETE CASCADE,
    logged_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    word TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT '',
    question_kind TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT '',
    user_input TEXT NOT NULL DEFAULT '',
    expected TEXT NOT NULL DEFAULT '',
    day INTEGER
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_key, id);
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    settings_json TEXT NOT NULL
);
"""

# 테이블을 만든 파일 경로를 기억해 두어, 같은 파일에는 다시 만들지 않는다.
_ready_paths = set()


def resolve_db_path(db_path=None):
    """DB 파일 경로. 지정하지 않으면 config의 DB_PATH를 쓴다."""
    return Path(db_path) if db_path is not None else DB_PATH


def connect(db_path=None):
    """SQLite 연결을 연다. 외래 키 규칙을 켜서 계정을 지우면 딸린 기록도 함께 지워지게 한다."""
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_missing_columns(connection):
    """예전에 만든 DB에 새로 생긴 열을 더한다. CREATE TABLE IF NOT EXISTS는 기존 표를 바꾸지 않기 때문이다."""
    history_columns = {row["name"] for row in connection.execute("PRAGMA table_info(history)").fetchall()}
    if "day" not in history_columns:
        connection.execute("ALTER TABLE history ADD COLUMN day INTEGER")
    user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "is_public" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0")


def ensure_schema(db_path=None):
    """테이블이 없으면 만든다. 같은 파일에서는 한 번만 실행한다."""
    path = resolve_db_path(db_path)
    if str(path) in _ready_paths:
        return
    connection = connect(path)
    try:
        connection.executescript(SCHEMA_SQL)
        _add_missing_columns(connection)
        connection.commit()
    finally:
        connection.close()
    _ready_paths.add(str(path))


@contextmanager
def transaction(db_path=None):
    """연결 하나를 열어 주고, 블록이 정상 끝나면 저장(commit), 오류가 나면 되돌리고(rollback) 닫는다."""
    ensure_schema(db_path)
    connection = connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
