#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 클로드 스마트 보카 - 계정·상태·추가 단어·이력을 SQLite(voca.db)에 읽고 쓰기, 계정 생성·초기화·삭제
# 파일 위치: src/user_store.py

import csv
import io
import json
import re

from config import USERNAME_PATTERN
from database import transaction
from timeutil import kst_now
from vocab import WordEntry

HISTORY_COLUMNS = ["일시", "구분", "단어", "방향", "유형", "결과", "입력값", "정답"]
# 이력 표의 열 이름: 화면과 CSV는 한글 이름(HISTORY_COLUMNS)을, DB는 영문 이름을 쓴다.
HISTORY_DB_COLUMNS = ["logged_at", "kind", "word", "direction", "question_kind", "result", "user_input", "expected"]
HISTORY_KEY_BY_DB_COLUMN = dict(zip(HISTORY_DB_COLUMNS, HISTORY_COLUMNS))
USERNAME_RE = re.compile(USERNAME_PATTERN)


def normalize_username(raw_name):
    """사용자명을 검사하고 저장용 소문자로 바꾼다. 형식이 맞지 않으면 None."""
    name = raw_name.strip()
    if not USERNAME_RE.match(name):
        return None
    return name.lower()


def empty_state():
    """새 계정의 기본 상태."""
    return {"assignments": [], "queue": [], "stats": {}, "memorized": {}}


def user_exists(username_key, db_path=None):
    with transaction(db_path) as connection:
        row = connection.execute("SELECT 1 FROM users WHERE user_key = ?", (username_key,)).fetchone()
    return row is not None


def list_user_keys(db_path=None):
    """계정 키 목록 (정렬)."""
    with transaction(db_path) as connection:
        rows = connection.execute("SELECT user_key FROM users ORDER BY user_key").fetchall()
    return [row["user_key"] for row in rows]


class UserStore:
    """한 사용자의 데이터를 다룬다. db_path를 바꾸면 테스트용 임시 DB를 쓸 수 있다."""

    def __init__(self, username_key, db_path=None):
        self.key = username_key
        self.db_path = db_path

    def exists(self):
        return user_exists(self.key, self.db_path)

    def create(self):
        """계정을 만든다. 이미 있으면 아무것도 하지 않는다."""
        with transaction(self.db_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO users (user_key, created_at) VALUES (?, ?)",
                (self.key, kst_now().isoformat(timespec="seconds")),
            )

    def delete(self):
        """계정과 그 계정의 상태·추가 단어·이력을 모두 지운다 (외래 키 CASCADE)."""
        with transaction(self.db_path) as connection:
            connection.execute("DELETE FROM users WHERE user_key = ?", (self.key,))

    def reset(self):
        """오답률, 이력, 과제 상태를 지운다. 계정과 추가 단어는 남긴다."""
        with transaction(self.db_path) as connection:
            connection.execute("DELETE FROM history WHERE user_key = ?", (self.key,))
        self.save_state(empty_state())

    def load_state(self):
        """상태를 읽는다. 저장된 상태가 없거나 깨졌으면 빈 상태로 시작한다."""
        with transaction(self.db_path) as connection:
            row = connection.execute("SELECT state_json FROM user_state WHERE user_key = ?", (self.key,)).fetchone()
        if row is None:
            return empty_state()
        try:
            loaded = json.loads(row["state_json"])
        except ValueError:
            return empty_state()
        if not isinstance(loaded, dict):
            return empty_state()
        return {**empty_state(), **loaded}

    def save_state(self, state):
        with transaction(self.db_path) as connection:
            connection.execute(
                "INSERT INTO user_state (user_key, state_json) VALUES (?, ?) "
                "ON CONFLICT(user_key) DO UPDATE SET state_json = excluded.state_json",
                (self.key, json.dumps(state, ensure_ascii=False)),
            )

    def load_custom_words(self):
        """사용자 추가 단어를 {단어: WordEntry}로 읽는다."""
        with transaction(self.db_path) as connection:
            rows = connection.execute(
                "SELECT word, pos, meanings_json, english_gloss, synonyms_json, example, source, license "
                "FROM custom_words WHERE user_key = ? ORDER BY word",
                (self.key,),
            ).fetchall()
        entries = {}
        for row in rows:
            entries[row["word"]] = WordEntry(
                word=row["word"],
                pos=row["pos"],
                meanings=json.loads(row["meanings_json"]),
                english_gloss=row["english_gloss"],
                synonyms=json.loads(row["synonyms_json"]),
                source=row["source"],
                license=row["license"],
                example=row["example"],
            )
        return entries

    def save_custom_words(self, custom_entries):
        """추가 단어 전체를 주어진 내용으로 바꾼다 (한 트랜잭션)."""
        with transaction(self.db_path) as connection:
            connection.execute("DELETE FROM custom_words WHERE user_key = ?", (self.key,))
            connection.executemany(
                "INSERT INTO custom_words (user_key, word, pos, meanings_json, english_gloss, synonyms_json, "
                "example, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        self.key, entry.word, entry.pos,
                        json.dumps(list(entry.meanings), ensure_ascii=False),
                        entry.english_gloss,
                        json.dumps(list(entry.synonyms), ensure_ascii=False),
                        entry.example, entry.source, entry.license,
                    )
                    for entry in custom_entries.values()
                ],
            )

    def append_history(self, rows):
        """이력 행(한글 열 이름의 dict 목록)을 끝에 추가한다."""
        if not rows:
            return
        values = [
            (self.key, row["일시"], row["구분"], row["단어"], row["방향"], row["유형"],
             row["결과"], row["입력값"], row["정답"])
            for row in rows
        ]
        with transaction(self.db_path) as connection:
            connection.executemany(
                "INSERT INTO history (user_key, logged_at, kind, word, direction, question_kind, result, "
                "user_input, expected) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )

    def read_history(self):
        """이력을 기록 순서대로 읽는다. 각 행은 한글 열 이름의 dict."""
        with transaction(self.db_path) as connection:
            rows = connection.execute(
                "SELECT logged_at, kind, word, direction, question_kind, result, user_input, expected "
                "FROM history WHERE user_key = ? ORDER BY id",
                (self.key,),
            ).fetchall()
        return [
            {HISTORY_KEY_BY_DB_COLUMN[column]: row[column] for column in HISTORY_DB_COLUMNS}
            for row in rows
        ]


def history_csv_bytes(rows):
    """이력 행 목록을 CSV 바이트로 만든다 (엑셀에서 한글이 깨지지 않도록 UTF-8 BOM을 붙인다)."""
    text_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(text_buffer, fieldnames=HISTORY_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return text_buffer.getvalue().encode("utf-8-sig")


def make_custom_entry(word, pos, meanings, synonyms=None, english_gloss="", example=""):
    """사용자 입력 단어를 WordEntry로 만든다."""
    return WordEntry(
        word=word,
        pos=pos,
        meanings=list(meanings),
        english_gloss=english_gloss,
        synonyms=list(synonyms or []),
        source="사용자 입력",
        license="",
        example=example,
    )
