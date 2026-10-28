#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 사용자별 파일(state.json, words.csv, history.csv) 읽기·쓰기, 계정 생성·초기화·삭제
# 파일 위치: src/user_store.py

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from config import USERNAME_PATTERN, USERS_DIR
from vocab import WordEntry, read_word_rows, write_word_rows

HISTORY_COLUMNS = ["일시", "구분", "단어", "방향", "유형", "결과", "입력값", "정답"]
USERNAME_RE = re.compile(USERNAME_PATTERN)


def normalize_username(raw_name):
    """사용자명을 검사하고 폴더 이름용 소문자로 바꾼다. 형식이 맞지 않으면 None."""
    name = raw_name.strip()
    if not USERNAME_RE.match(name):
        return None
    return name.lower()


def empty_state():
    """새 계정의 기본 상태."""
    return {"assignments": [], "queue": [], "stats": {}, "memorized": {}}


def write_json_atomic(path, data):
    """JSON을 임시 파일에 쓴 뒤 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)
    temp_path.replace(path)


class UserStore:
    """한 사용자의 파일을 다룬다. base_dir을 바꾸면 테스트용 임시 폴더를 쓸 수 있다."""

    def __init__(self, username_key, base_dir=USERS_DIR):
        self.key = username_key
        self.dir = Path(base_dir) / username_key
        self.state_path = self.dir / "state.json"
        self.words_path = self.dir / "words.csv"
        self.history_path = self.dir / "history.csv"

    def exists(self):
        return self.dir.is_dir()

    def create(self):
        self.dir.mkdir(parents=True, exist_ok=True)

    def delete(self):
        """계정 폴더 전체를 지운다."""
        if self.dir.exists():
            shutil.rmtree(self.dir)

    def reset(self):
        """오답률, 이력, 과제 상태를 지운다. 계정과 추가 단어는 남긴다."""
        write_json_atomic(self.state_path, empty_state())
        if self.history_path.exists():
            self.history_path.unlink()

    def load_state(self):
        """상태 파일을 읽는다. 깨졌으면 파일 이름을 바꿔 남기고 빈 상태로 시작한다."""
        if not self.state_path.exists():
            return empty_state()
        try:
            with self.state_path.open(encoding="utf-8") as json_file:
                loaded = json.load(json_file)
            if not isinstance(loaded, dict):
                raise ValueError("state.json 형식이 아닙니다")
            return {**empty_state(), **loaded}
        except (OSError, ValueError):
            quarantine_file(self.state_path)
            return empty_state()

    def save_state(self, state):
        write_json_atomic(self.state_path, state)

    def load_custom_words(self):
        """사용자 추가 단어를 {단어: WordEntry}로 읽는다."""
        return {entry.word: entry for entry in read_word_rows(self.words_path)}

    def save_custom_words(self, custom_entries):
        write_word_rows(self.words_path, list(custom_entries.values()))

    def append_history(self, rows):
        """이력 행(dict 목록)을 끝에 추가한다. 파일이 없으면 머리글을 먼저 쓴다."""
        if not rows:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        is_new_file = not self.history_path.exists()
        with self.history_path.open("a", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=HISTORY_COLUMNS)
            if is_new_file:
                writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def read_history(self):
        if not self.history_path.exists():
            return []
        with self.history_path.open(encoding="utf-8-sig", newline="") as csv_file:
            return list(csv.DictReader(csv_file))


def list_user_keys(base_dir=USERS_DIR):
    """계정 폴더 이름 목록 (정렬)."""
    if not Path(base_dir).is_dir():
        return []
    return sorted(path.name for path in Path(base_dir).iterdir() if path.is_dir())


def quarantine_file(path):
    """깨진 파일을 시각을 붙여 옆으로 옮긴다. 기록을 지우지 않고 남겨 둔다."""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        path.replace(target)
    except OSError:
        pass


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
