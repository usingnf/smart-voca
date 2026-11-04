#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - 클로드 스마트 보카 - 로컬 후보 풀(korean_candidates.json)에서 기존 voca.csv 단어를 제외하고 2000개를 추가
# 파일 위치: ai-agent/scripts/261104-영단어추가.py

import csv
import json
import os
import random
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CANDIDATE_PATH = RAW_DIR / "korean_candidates.json"
VOCA_PATH = DATA_DIR / "voca.csv"
BACKUP_PATH = RAW_DIR / "voca_before_add2000.csv"
TEMP_PATH = VOCA_PATH.with_suffix(".csv.tmp")

ADD_SIZE = 2000
RANDOM_SEED = 20261104
SOURCE_NAME = "kaikki.org (English Wiktionary 추출, 2026-09-02 덤프)"
LICENSE_NAME = "CC BY-SA 4.0 / GFDL (Wiktionary 원저작물)"


def load_existing_rows():
    with VOCA_PATH.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader.fieldnames), list(reader)


def main():
    fieldnames, existing_rows = load_existing_rows()
    existing_words = {row["단어"] for row in existing_rows}

    candidate_pool = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    remaining_words = sorted(word for word in candidate_pool if word not in existing_words)
    if len(remaining_words) < ADD_SIZE:
        raise SystemExit(f"추가 가능한 후보가 부족합니다: {len(remaining_words)}개")

    random_generator = random.Random(RANDOM_SEED)
    added_words = random_generator.sample(remaining_words, ADD_SIZE)

    new_rows = []
    for word in added_words:
        record = candidate_pool[word]
        new_row = {name: "" for name in fieldnames}
        new_row.update({
            "단어": word,
            "품사": ", ".join(record["pos"]),
            "한글뜻": ", ".join(record["korean"]),
            "영문뜻": record["english"],
            "출처": SOURCE_NAME,
            "라이선스": LICENSE_NAME,
        })
        new_rows.append(new_row)

    all_rows = sorted(existing_rows + new_rows, key=lambda row: row["단어"])

    # 원본을 먼저 백업한 뒤, 임시 파일에 쓰고 교체한다.
    shutil.copy2(VOCA_PATH, BACKUP_PATH)
    with TEMP_PATH.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    os.replace(TEMP_PATH, VOCA_PATH)

    print(f"기존 {len(existing_rows)}개 + 추가 {len(new_rows)}개 = 총 {len(all_rows)}개")
    print(f"백업: {BACKUP_PATH}")
    print(f"저장: {VOCA_PATH}")


if __name__ == "__main__":
    main()
