#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 클로드 스마트 보카 - 기존 파일 저장소(users/ 폴더, settings.json)를 SQLite(voca.db)로 옮기는 1회성 스크립트
# 파일 위치: ai-agent/scripts/261125-파일저장소를SQLite로옮기기.py
# 실행 (프로젝트 루트에서): py -3.11 "ai-agent/scripts/261125-파일저장소를SQLite로옮기기.py" --data-dir data --db data/voca.db
# 원본 파일은 지우지 않는다. 이미 DB에 있는 계정과 옵션은 건너뛴다.

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import BASE_DIR, DB_PATH  # noqa: E402
from database import transaction  # noqa: E402
from settings import AppSettings, save_settings  # noqa: E402
from user_store import HISTORY_COLUMNS, UserStore, empty_state, user_exists  # noqa: E402
from vocab import read_word_rows  # noqa: E402


def read_json_or_default(path, default):
    """JSON 파일을 읽는다. 없거나 깨졌으면 기본값을 쓰고 알린다."""
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as json_file:
            loaded = json.load(json_file)
        return loaded if isinstance(loaded, dict) else default
    except (OSError, ValueError):
        print(f"  경고: {path.name}을(를) 읽을 수 없어 기본값으로 옮깁니다.")
        return default


def read_history_rows(path):
    """history.csv를 한글 열 이름의 dict 목록으로 읽는다."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        return [{column: row.get(column, "") for column in HISTORY_COLUMNS} for row in csv.DictReader(csv_file)]


def migrate_user(user_dir, db_path):
    """계정 폴더 하나를 DB로 옮긴다. 옮긴 항목 수를 문자열로 돌려준다."""
    key = user_dir.name
    if user_exists(key, db_path):
        return f"{key}: 건너뜀 (이미 DB에 있음)"
    store = UserStore(key, db_path=db_path)
    store.create()
    state = {**empty_state(), **read_json_or_default(user_dir / "state.json", {})}
    store.save_state(state)
    custom_entries = {entry.word: entry for entry in read_word_rows(user_dir / "words.csv")}
    store.save_custom_words(custom_entries)
    history_rows = read_history_rows(user_dir / "history.csv")
    store.append_history(history_rows)
    return f"{key}: 추가 단어 {len(custom_entries)}개, 이력 {len(history_rows)}행 옮김"


def settings_row_exists(db_path):
    with transaction(db_path) as connection:
        return connection.execute("SELECT 1 FROM app_settings WHERE id = 1").fetchone() is not None


def migrate_settings(data_dir, db_path):
    """settings.json을 옵션 표로 옮긴다. DB에 이미 옵션이 있으면 건너뛴다."""
    settings_path = data_dir / "settings.json"
    if not settings_path.exists():
        return "settings.json 없음: 건너뜀"
    if settings_row_exists(db_path):
        return "옵션: 건너뜀 (DB에 이미 옵션이 있음)"
    data = read_json_or_default(settings_path, {})
    known = {key: value for key, value in data.items() if key in AppSettings.__dataclass_fields__}
    try:
        settings = AppSettings(**known).sanitized()
    except (TypeError, ValueError):
        print("  경고: settings.json 값이 맞지 않아 기본 옵션으로 옮깁니다.")
        settings = AppSettings()
    save_settings(settings, db_path)
    return "옵션: 옮김"


def main():
    parser = argparse.ArgumentParser(description="파일 저장소를 SQLite로 옮깁니다.")
    parser.add_argument("--data-dir", type=Path, default=BASE_DIR, help="users/ 폴더와 settings.json이 있는 폴더")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="옮겨 넣을 SQLite 파일")
    args = parser.parse_args()

    users_dir = args.data_dir / "users"
    print(f"원본 폴더: {args.data_dir}")
    print(f"대상 DB:   {args.db}")
    if users_dir.is_dir():
        for user_dir in sorted(path for path in users_dir.iterdir() if path.is_dir()):
            print(" ", migrate_user(user_dir, args.db))
    else:
        print("  users/ 폴더가 없어 계정은 옮기지 않습니다.")
    print(" ", migrate_settings(args.data_dir, args.db))
    print("완료. 원본 파일은 그대로 두었습니다.")


if __name__ == "__main__":
    main()
