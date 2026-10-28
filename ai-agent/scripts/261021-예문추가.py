#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - voca.csv 단어들의 Kaikki 예문을 '예문' 열로 추가
# 파일 위치: ai-agent/scripts/261021-예문추가.py

import csv
import gzip
import json
import os
import urllib.request
from pathlib import Path

RAW_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOCA_PATH = PROJECT_ROOT / "data" / "voca.csv"
EXAMPLE_COLUMN = "예문"
MAX_EXAMPLE_LENGTH = 150
PROGRESS_INTERVAL = 2000000


def load_voca_rows():
    with VOCA_PATH.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames)


def iter_raw_lines():
    with urllib.request.urlopen(RAW_URL, timeout=120) as response:
        with gzip.GzipFile(fileobj=response) as gz_stream:
            for raw_line in gz_stream:
                yield raw_line


def extract_example(entry):
    """엔트리의 뜻(sense)에 달린 예문 중 길이 제한 안의 첫 예문을 고른다."""
    for sense in entry.get("senses", []):
        for example in sense.get("examples", []):
            text = (example.get("text") or "").strip()
            if text and len(text) <= MAX_EXAMPLE_LENGTH:
                return text
    return ""


def collect_examples(target_words):
    examples_by_word = {}
    scanned_lines = 0
    for raw_line in iter_raw_lines():
        scanned_lines += 1
        if scanned_lines % PROGRESS_INTERVAL == 0:
            print(f"  scanned {scanned_lines:,} lines")

        if b'"examples"' not in raw_line:
            continue

        entry = json.loads(raw_line)
        word = entry.get("word", "")
        if entry.get("lang_code") != "en" or word not in target_words or word in examples_by_word:
            continue

        example = extract_example(entry)
        if example:
            examples_by_word[word] = example

    print(f"scan done: {scanned_lines:,} lines")
    return examples_by_word


def write_voca_rows(rows, fieldnames, examples_by_word):
    if EXAMPLE_COLUMN not in fieldnames:
        fieldnames = fieldnames + [EXAMPLE_COLUMN]

    temp_path = VOCA_PATH.with_suffix(".csv.tmp")
    with temp_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row[EXAMPLE_COLUMN] = examples_by_word.get(row["단어"], "")
            writer.writerow(row)

    os.replace(temp_path, VOCA_PATH)


def main():
    rows, fieldnames = load_voca_rows()
    target_words = {row["단어"] for row in rows}

    examples_by_word = collect_examples(target_words)
    print(f"words with examples: {len(examples_by_word)} / {len(target_words)}")

    write_voca_rows(rows, fieldnames, examples_by_word)
    print(f"saved: {VOCA_PATH}")


if __name__ == "__main__":
    main()
