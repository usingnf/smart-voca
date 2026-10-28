#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - voca.csv 로드, 사용자 단어 병합, 유의어 검색
# 파일 위치: src/vocab.py

import csv
from dataclasses import dataclass, field

from config import VOCA_PATH

COLUMN_WORD = "단어"
COLUMN_POS = "품사"
COLUMN_MEANING = "한글뜻"
COLUMN_GLOSS = "영문뜻"
COLUMN_SOURCE = "출처"
COLUMN_LICENSE = "라이선스"
COLUMN_SYNONYM = "유의어"
COLUMN_EXAMPLE = "예문"
CSV_COLUMNS = [COLUMN_WORD, COLUMN_POS, COLUMN_MEANING, COLUMN_GLOSS,
               COLUMN_SOURCE, COLUMN_LICENSE, COLUMN_SYNONYM, COLUMN_EXAMPLE]
LIST_SEPARATOR = ", "
USER_SOURCE = "사용자 입력"


@dataclass
class WordEntry:
    """단어 한 개. meanings는 한글 뜻 목록이며 비어 있을 수 없다."""

    word: str
    pos: str
    meanings: list
    english_gloss: str = ""
    synonyms: list = field(default_factory=list)
    source: str = ""
    license: str = ""
    example: str = ""


def split_list(text):
    """쉼표로 구분된 문자열을 목록으로 바꾼다. 빈 항목은 버린다."""
    return [item.strip() for item in text.split(",") if item.strip()]


def join_list(items):
    """목록을 CSV 셀 문자열로 바꾼다."""
    return LIST_SEPARATOR.join(items)


def entry_to_row(entry):
    """WordEntry를 CSV 한 행(dict)으로 바꾼다."""
    return {
        COLUMN_WORD: entry.word,
        COLUMN_POS: entry.pos,
        COLUMN_MEANING: join_list(entry.meanings),
        COLUMN_GLOSS: entry.english_gloss,
        COLUMN_SOURCE: entry.source,
        COLUMN_LICENSE: entry.license,
        COLUMN_SYNONYM: join_list(entry.synonyms),
        COLUMN_EXAMPLE: entry.example,
    }


def row_to_entry(row):
    """CSV 한 행(dict)을 WordEntry로 바꾼다. 한글 뜻이 없으면 None."""
    meanings = split_list(row.get(COLUMN_MEANING, ""))
    word = row.get(COLUMN_WORD, "").strip()
    if not word or not meanings:
        return None
    return WordEntry(
        word=word,
        pos=row.get(COLUMN_POS, "").strip(),
        meanings=meanings,
        english_gloss=row.get(COLUMN_GLOSS, "").strip(),
        synonyms=split_list(row.get(COLUMN_SYNONYM, "")),
        source=row.get(COLUMN_SOURCE, "").strip(),
        license=row.get(COLUMN_LICENSE, "").strip(),
        example=row.get(COLUMN_EXAMPLE, "").strip(),
    )


def read_word_rows(path):
    """CSV 파일을 읽어 WordEntry 목록을 만든다. 파일이 없으면 빈 목록."""
    if not path.exists():
        return []
    entries = []
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            entry = row_to_entry(row)
            if entry is not None:
                entries.append(entry)
    return entries


def write_word_rows(path, entries):
    """WordEntry 목록을 CSV로 저장한다. 임시 파일에 쓴 뒤 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".csv.tmp")
    with temp_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry_to_row(entry))
    temp_path.replace(path)


class Vocabulary:
    """기본 단어 풀 (voca.csv). 사용자 단어는 merged()로 합친다."""

    def __init__(self, entries):
        self.base = {entry.word: entry for entry in entries}

    @classmethod
    def load(cls, path=VOCA_PATH):
        return cls(read_word_rows(path))

    def __len__(self):
        return len(self.base)

    def merged(self, custom_entries):
        """기본 단어에 사용자 단어를 덮어쓴 풀을 만든다. 같은 단어는 사용자 항목이 우선."""
        pool = dict(self.base)
        for entry in custom_entries.values():
            pool[entry.word] = entry
        return pool


POS_LABELS = {"noun": "명사", "verb": "동사", "adj": "형용사", "adv": "부사", "other": "기타"}
MAIN_POS_KEYS = ("noun", "verb", "adj", "adv")


def entry_pos_keys(entry):
    """단어가 속한 품사 키 집합. 'noun, verb'처럼 여러 개면 모두 담는다.

    네 가지 주요 품사에 없는 값과 빈 값은 'other'(기타)로 묶는다.
    """
    keys = set()
    for token in split_list(entry.pos):
        keys.add(token if token in MAIN_POS_KEYS else "other")
    return keys or {"other"}


def filter_by_pos(pool, selected_keys):
    """선택한 품사 중 하나라도 속한 단어만 남긴다."""
    return {word: entry for word, entry in pool.items() if entry_pos_keys(entry) & set(selected_keys)}


def search_by_english(pool, query):
    """영어 단어로 찾는다. 대소문자는 무시한다."""
    entry = pool.get(query.strip().lower())
    return [entry] if entry else []


def search_by_meaning(pool, query, limit=20):
    """한글 뜻으로 찾는다. 뜻이 정확히 같은 단어를 먼저 보여 주고, 그다음 포함 관계를 본다."""
    query = query.strip()
    exact, partial = [], []
    for entry in pool.values():
        if query in entry.meanings:
            exact.append(entry)
        elif any(query in meaning for meaning in entry.meanings):
            partial.append(entry)
    exact.sort(key=lambda entry: entry.word)
    partial.sort(key=lambda entry: entry.word)
    return (exact + partial)[:limit]
