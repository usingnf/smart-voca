#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 단어 CSV(영단어,뜻) 텍스트를 읽어 등록할 단어와 오류 줄을 나눈다
# 파일 위치: src/word_import.py

import csv
import io

from config import IMPORT_MAX_LINES
from vocab import WORD_PATTERN

HEADER_ROW = ["영단어", "뜻"]
MEANING_SEPARATORS = (",", "，")


def split_meanings(text):
    """뜻 칸을 쉼표로 나눈다. 따옴표 없이 쉼표가 들어와도 뜻이 쪼개지도록 다시 합친 뒤 나눈다."""
    meanings = [text]
    for separator in MEANING_SEPARATORS:
        meanings = [part for item in meanings for part in item.split(separator)]
    return [meaning.strip() for meaning in meanings if meaning.strip()]


def parse_word_csv(text):
    """CSV 텍스트를 읽는다. UTF-8 BOM과 첫 줄 머리글(영단어,뜻)은 건너뛴다.

    반환: (entries, errors)
      entries: [{"word": 영단어(소문자), "meanings": [뜻, ...], "line": 줄 번호}, ...]
      errors:  [{"line": 줄 번호, "reason": 오류 이유}, ...]
    파일 안의 중복 단어는 여기서 막지 않는다. 등록할 때(session.add_words_bulk) 건너뛴다.
    """
    if text.count("\n") + 1 > IMPORT_MAX_LINES:
        raise ValueError(f"한 번에 {IMPORT_MAX_LINES}줄까지 가져올 수 있습니다.")

    entries, errors = [], []
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    for line_no, row in enumerate(reader, start=1):
        if not any(cell.strip() for cell in row):
            continue
        if line_no == 1 and [cell.strip() for cell in row[:2]] == HEADER_ROW:
            continue
        if len(row) < 2:
            errors.append({"line": line_no, "reason": "쉼표로 나눈 두 칸(영단어, 뜻)이 필요합니다."})
            continue
        word = row[0].strip().lower()
        if not WORD_PATTERN.match(word):
            errors.append({"line": line_no, "reason": "영단어는 영문자, 공백, 하이픈, 작은따옴표만 쓸 수 있습니다."})
            continue
        meanings = split_meanings(",".join(row[1:]))
        if not meanings:
            errors.append({"line": line_no, "reason": "뜻이 비어 있습니다."})
            continue
        entries.append({"word": word, "meanings": meanings, "line": line_no})
    return entries, errors
