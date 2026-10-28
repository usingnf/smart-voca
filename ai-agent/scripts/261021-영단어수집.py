#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - Kaikki(English Wiktionary 추출)에서 한국어 번역이 있는 영단어 2000개를 뽑아 voca.csv 생성
# 파일 위치: ai-agent/scripts/261021-영단어수집.py

import csv
import gzip
import json
import random
import re
import urllib.request
from pathlib import Path

RAW_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CANDIDATE_PATH = RAW_DIR / "korean_candidates.json"
VOCA_PATH = DATA_DIR / "voca.csv"

SAMPLE_SIZE = 2000
RANDOM_SEED = 20261021
TARGET_POS = {"noun", "verb", "adj", "adv"}
WORD_PATTERN = re.compile(r"^[a-z]{3,12}$")
MAX_KOREAN_MEANINGS = 3
PROGRESS_INTERVAL = 2000000
SOURCE_NAME = "kaikki.org (English Wiktionary 추출, 2026-09-02 덤프)"
LICENSE_NAME = "CC BY-SA 4.0 / GFDL (Wiktionary 원저작물)"


def iter_raw_lines():
    """원시 JSONL.gz를 네트워크에서 스트리밍으로 한 줄씩 읽는다 (전체 파일을 디스크에 저장하지 않음)."""
    with urllib.request.urlopen(RAW_URL, timeout=120) as response:
        with gzip.GzipFile(fileobj=response) as gz_stream:
            for raw_line in gz_stream:
                yield raw_line


def extract_korean_entry(entry):
    """영어 표제어 엔트리에서 한국어 번역이 있으면 (단어, 품사, 한국어 번역 목록, 영문 뜻)을 반환한다. 조건에 안 맞으면 None."""
    word = entry.get("word", "")
    if entry.get("lang_code") != "en" or not WORD_PATTERN.match(word):
        return None

    part_of_speech = entry.get("pos", "")
    if part_of_speech not in TARGET_POS:
        return None

    korean_words = [
        translation.get("word", "")
        for translation in entry.get("translations", [])
        if translation.get("lang_code") == "ko" and translation.get("word")
    ]
    if not korean_words:
        return None

    english_gloss = ""
    for sense in entry.get("senses", []):
        glosses = sense.get("glosses", [])
        if glosses:
            english_gloss = glosses[0]
            break

    return word, part_of_speech, korean_words, english_gloss


def build_candidate_pool():
    """원시 데이터를 한 번 훑어 한국어 번역이 있는 영단어 후보 풀을 만든다.

    '"lang_code": "ko"' 문자열이 없는 줄은 JSON 파싱을 건너뛰어 처리 시간을 줄인다.
    """
    candidate_pool = {}
    scanned_lines = 0

    for raw_line in iter_raw_lines():
        scanned_lines += 1
        if scanned_lines % PROGRESS_INTERVAL == 0:
            print(f"  스캔 {scanned_lines:,}줄, 후보 {len(candidate_pool):,}개")

        if b'"lang_code": "ko"' not in raw_line:
            continue

        extracted = extract_korean_entry(json.loads(raw_line))
        if extracted is None:
            continue

        word, part_of_speech, korean_words, english_gloss = extracted
        record = candidate_pool.setdefault(word, {"pos": [], "korean": [], "english": ""})

        if part_of_speech not in record["pos"]:
            record["pos"].append(part_of_speech)

        for korean_word in korean_words:
            if korean_word not in record["korean"] and len(record["korean"]) < MAX_KOREAN_MEANINGS:
                record["korean"].append(korean_word)

        if not record["english"]:
            record["english"] = english_gloss

    print(f"스캔 완료: {scanned_lines:,}줄, 후보 단어 {len(candidate_pool):,}개")
    return candidate_pool


def write_voca_csv(candidate_pool):
    """후보 풀에서 고정 시드로 SAMPLE_SIZE개를 무작위 추출해 voca.csv로 저장한다.

    utf-8-sig(BOM 포함)로 저장해 Excel에서 한글이 깨지지 않게 한다.
    """
    if len(candidate_pool) < SAMPLE_SIZE:
        raise SystemExit(f"후보 단어가 {SAMPLE_SIZE}개보다 적습니다: {len(candidate_pool)}개")

    random_generator = random.Random(RANDOM_SEED)
    sampled_words = random_generator.sample(sorted(candidate_pool), SAMPLE_SIZE)

    with VOCA_PATH.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["단어", "품사", "한글뜻", "영문뜻", "출처", "라이선스"])
        for word in sorted(sampled_words):
            record = candidate_pool[word]
            writer.writerow([
                word,
                ", ".join(record["pos"]),
                ", ".join(record["korean"]),
                record["english"],
                SOURCE_NAME,
                LICENSE_NAME,
            ])

    print(f"저장 완료: {VOCA_PATH} ({SAMPLE_SIZE}개)")


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    candidate_pool = build_candidate_pool()
    CANDIDATE_PATH.write_text(json.dumps(candidate_pool, ensure_ascii=False), encoding="utf-8")
    print(f"후보 풀 저장: {CANDIDATE_PATH}")

    write_voca_csv(candidate_pool)


if __name__ == "__main__":
    main()
