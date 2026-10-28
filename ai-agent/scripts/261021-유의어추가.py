#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - voca.csv 단어들의 Kaikki 유의어를 '유의어' 열로 추가
# 파일 위치: ai-agent/scripts/261021-유의어추가.py

import csv
import gzip
import json
import os
import urllib.request
from pathlib import Path

RAW_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOCA_PATH = PROJECT_ROOT / "data" / "voca.csv"
SYNONYM_COLUMN = "유의어"
MAX_SYNONYMS = 10
PROGRESS_INTERVAL = 2000000


def load_voca_rows():
    """voca.csv를 읽어 행 목록과 열 이름 목록을 반환한다."""
    with VOCA_PATH.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames)


def iter_raw_lines():
    """원시 JSONL.gz를 네트워크에서 스트리밍으로 한 줄씩 읽는다 (전체 파일을 디스크에 저장하지 않음)."""
    with urllib.request.urlopen(RAW_URL, timeout=120) as response:
        with gzip.GzipFile(fileobj=response) as gz_stream:
            for raw_line in gz_stream:
                yield raw_line


def extract_synonym_words(entry):
    """엔트리의 최상위 유의어와 뜻(sense)별 유의어에서 단어만 모아 중복 없이 반환한다."""
    candidates = list(entry.get("synonyms", []))
    for sense in entry.get("senses", []):
        candidates.extend(sense.get("synonyms", []))

    synonym_words = []
    for candidate in candidates:
        synonym = candidate.get("word", "") if isinstance(candidate, dict) else ""
        if synonym and synonym not in synonym_words:
            synonym_words.append(synonym)
    return synonym_words


def collect_synonyms(target_words):
    """원시 데이터를 한 번 훑어 대상 단어별 유의어 목록을 만든다.

    '"synonyms"' 문자열이 없는 줄은 JSON 파싱을 건너뛴다.
    """
    synonyms_by_word = {word: [] for word in target_words}
    scanned_lines = 0

    for raw_line in iter_raw_lines():
        scanned_lines += 1
        if scanned_lines % PROGRESS_INTERVAL == 0:
            print(f"  scanned {scanned_lines:,} lines")

        if b'"synonyms"' not in raw_line:
            continue

        entry = json.loads(raw_line)
        word = entry.get("word", "")
        if entry.get("lang_code") != "en" or word not in synonyms_by_word:
            continue

        bucket = synonyms_by_word[word]
        for synonym in extract_synonym_words(entry):
            if synonym not in bucket and len(bucket) < MAX_SYNONYMS:
                bucket.append(synonym)

    print(f"scan done: {scanned_lines:,} lines")
    return synonyms_by_word


def write_voca_rows(rows, fieldnames, synonyms_by_word):
    """유의어 열을 채워 임시 파일에 쓴 뒤 원본을 교체한다. 중간 실패 시 원본이 남도록 한다."""
    if SYNONYM_COLUMN not in fieldnames:
        fieldnames = fieldnames + [SYNONYM_COLUMN]

    temp_path = VOCA_PATH.with_suffix(".csv.tmp")
    with temp_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row[SYNONYM_COLUMN] = ", ".join(synonyms_by_word.get(row["단어"], []))
            writer.writerow(row)

    os.replace(temp_path, VOCA_PATH)


def main():
    rows, fieldnames = load_voca_rows()
    target_words = [row["단어"] for row in rows]

    synonyms_by_word = collect_synonyms(target_words)
    covered_count = sum(1 for synonyms in synonyms_by_word.values() if synonyms)
    print(f"words with synonyms: {covered_count} / {len(target_words)}")

    write_voca_rows(rows, fieldnames, synonyms_by_word)
    print(f"saved: {VOCA_PATH}")


if __name__ == "__main__":
    main()
