#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 기본 기능 보완 테스트: CSV 가져오기, 일차·진도, 이력 일차, 가중 출제, 자주 틀린 단어 섞기
# 파일 위치: tests/test_basic_requirements.py

import random
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from daily import day_number, pick_review_words  # noqa: E402
from database import ensure_schema  # noqa: E402
from sampling import pick_weighted_words, word_weight  # noqa: E402
from session import UserSession  # noqa: E402
from user_store import UserStore  # noqa: E402
from vocab import Vocabulary, WordEntry  # noqa: E402
from word_import import parse_word_csv  # noqa: E402


def make_entry(word, meanings=("뜻",), pos="noun"):
    return WordEntry(word=word, pos=pos, meanings=list(meanings))


class FakeStore:
    """세션이 쓰는 저장소 중 사용자 단어 저장만 흉내 낸다."""

    def __init__(self):
        self.saved = None
        self.history_rows = []

    def save_custom_words(self, custom):
        self.saved = dict(custom)

    def append_history(self, rows):
        self.history_rows.extend(rows)


def make_session(base_words, state=None):
    session = UserSession.__new__(UserSession)
    session.vocabulary = Vocabulary([make_entry(word) for word in base_words])
    session.custom = {}
    session.store = FakeStore()
    session.state = state or {"memorized": {}, "assignments": [], "stats": {}, "queue": [], "favorites": []}
    session.rng = random.Random(1)
    session.refresh_pool()
    return session


class ParseWordCsvTests(unittest.TestCase):
    def test_bom_and_header_are_skipped(self):
        text = "﻿영단어,뜻\napple,사과\n"
        entries, errors = parse_word_csv(text)
        self.assertEqual(errors, [])
        self.assertEqual([(e["word"], e["meanings"]) for e in entries], [("apple", ["사과"])])

    def test_quoted_and_unquoted_commas_both_split_meanings(self):
        text = 'abacus,수판, 산판\n"bank","은행, 둑"\n'
        entries, _ = parse_word_csv(text)
        self.assertEqual(entries[0]["meanings"], ["수판", "산판"])
        self.assertEqual(entries[1]["meanings"], ["은행", "둑"])

    def test_bad_rows_are_reported_with_line_numbers(self):
        text = "apple,사과\n123,숫자\nnoword\npear,\n"
        entries, errors = parse_word_csv(text)
        self.assertEqual([e["word"] for e in entries], ["apple"])
        self.assertEqual([item["line"] for item in errors], [2, 3, 4])

    def test_too_many_lines_is_rejected(self):
        from config import IMPORT_MAX_LINES
        with self.assertRaises(ValueError):
            parse_word_csv("a,뜻\n" * (IMPORT_MAX_LINES + 1))


class BulkAddTests(unittest.TestCase):
    def test_existing_and_duplicate_words_are_skipped(self):
        session = make_session(["apple"])
        result = session.add_words_bulk([
            ("apple", ["사과"]),      # 기본 단어와 겹침
            ("pear", ["배"]),
            ("pear", ["배 (중복)"]),  # 같은 파일 안 중복
            ("plum", ["자두"]),
        ])
        self.assertEqual(result, {"added": 2, "skipped": 2})
        self.assertIn("pear", session.custom)
        self.assertIn("plum", session.pool)
        self.assertEqual(set(session.store.saved), {"pear", "plum"})

    def test_imported_words_get_other_pos(self):
        session = make_session([])
        session.add_words_bulk([("pear", ["배"])])
        self.assertEqual(session.custom["pear"].pos, "other")


class WeightedTestTests(unittest.TestCase):
    def test_never_asked_outweighs_asked_word(self):
        today = date(2026, 11, 26)
        never = word_weight({}, "new", today)
        asked = word_weight({"old": {"asked": 3, "wrong": 0, "last_asked": today.isoformat()}}, "old", today)
        self.assertGreater(never, asked)

    def test_high_error_rate_and_stale_words_get_more_weight(self):
        today = date(2026, 11, 26)
        stats = {
            "fresh_ok": {"asked": 4, "wrong": 0, "last_asked": today.isoformat()},
            "fresh_bad": {"asked": 4, "wrong": 4, "last_asked": today.isoformat()},
            "stale_ok": {"asked": 4, "wrong": 0, "last_asked": (today - timedelta(days=30)).isoformat()},
        }
        self.assertGreater(word_weight(stats, "fresh_bad", today), word_weight(stats, "fresh_ok", today))
        self.assertGreater(word_weight(stats, "stale_ok", today), word_weight(stats, "fresh_ok", today))

    def test_picks_are_unique_and_favor_never_asked_words(self):
        today = date(2026, 11, 26)
        candidates = {f"w{i:03d}": make_entry(f"w{i:03d}") for i in range(100)}
        stats = {word: {"asked": 2, "wrong": 0, "last_asked": today.isoformat()} for word in candidates}
        never_asked = {f"w{i:03d}" for i in range(10)}
        for word in never_asked:
            del stats[word]

        rng = random.Random(42)
        hits = 0
        for _ in range(200):
            picked = pick_weighted_words(candidates, stats, today, 10, rng)
            words = [entry.word for entry in picked]
            self.assertEqual(len(words), len(set(words)))
            hits += sum(1 for word in words if word in never_asked)
        # 균등 추출이면 뽑힌 10개 중 10%쯤(1개) 안 본 단어가 나온다. 가중치 3 대 1이라 그보다 확실히 많아야 한다.
        self.assertGreater(hits / (200 * 10), 0.18)

    def test_count_is_capped_by_candidates(self):
        candidates = {"a": make_entry("a"), "b": make_entry("b")}
        picked = pick_weighted_words(candidates, {}, date(2026, 11, 26), 50, random.Random(1))
        self.assertEqual(len(picked), 2)


class DayNumberTests(unittest.TestCase):
    def test_day_number_counts_assignments_in_order(self):
        state = {"assignments": [{"date": "2026-11-24"}, {"date": "2026-11-25"}]}
        self.assertEqual(day_number(state, date(2026, 11, 24)), 1)
        self.assertEqual(day_number(state, date(2026, 11, 25)), 2)
        self.assertIsNone(day_number(state, date(2026, 11, 26)))

    def test_progress_counts_memorized_words_in_pool(self):
        today = date(2026, 11, 26)
        state = {"memorized": {"2026-11-25": ["apple"], "2026-11-26": ["apple", "pear", "ghost"]},
                 "assignments": [{"date": "2026-11-26"}]}
        session = make_session(["apple", "pear", "plum"], state=state)
        self.assertEqual(session.progress(today), {"day": 1, "memorized": 2, "total": 3})


class MemorizeDayTests(unittest.TestCase):
    def test_memorize_history_row_carries_day_number(self):
        from timeutil import kst_today
        today = kst_today()
        state = {"memorized": {}, "assignments": [{"date": (today - timedelta(days=1)).isoformat()},
                                                   {"date": today.isoformat()}]}
        session = make_session(["apple"], state=state)
        session.save = lambda: None
        session.record_memorize("apple")
        self.assertEqual(session.store.history_rows[0]["일차"], 2)


class ReviewMixTests(unittest.TestCase):
    def test_review_includes_frequently_wrong_words(self):
        pool = {f"w{i:02d}": make_entry(f"w{i:02d}") for i in range(30)}
        stats = {"w20": {"asked": 4, "wrong": 4}, "w21": {"asked": 4, "wrong": 3}}
        yesterday = [f"w{i:02d}" for i in range(10)]
        state = {"queue": [], "stats": stats}
        review = pick_review_words(state, yesterday, 10, pool, random.Random(3))
        self.assertEqual(len(review), 10)
        self.assertEqual(len(set(review)), 10)
        self.assertIn("w20", review)
        self.assertIn("w21", review)
        # 전날 단어도 함께 남아 있어야 한다 (일부 섞기)
        self.assertTrue(any(word in yesterday for word in review))

    def test_without_error_history_review_falls_back_to_yesterday(self):
        pool = {f"w{i:02d}": make_entry(f"w{i:02d}") for i in range(30)}
        yesterday = [f"w{i:02d}" for i in range(10)]
        review = pick_review_words({"queue": [], "stats": {}}, yesterday, 4, pool, random.Random(3))
        self.assertEqual(len(review), 4)
        self.assertTrue(set(review) <= set(yesterday))


class HistoryDayColumnTests(unittest.TestCase):
    def test_old_database_gets_day_column_and_round_trips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "old.db"
            connection = sqlite3.connect(str(db_path))
            connection.execute(
                "CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_key TEXT NOT NULL, "
                "logged_at TEXT NOT NULL, kind TEXT NOT NULL, word TEXT NOT NULL, direction TEXT NOT NULL DEFAULT '', "
                "question_kind TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '', "
                "user_input TEXT NOT NULL DEFAULT '', expected TEXT NOT NULL DEFAULT '')")
            connection.commit()
            connection.close()

            ensure_schema(db_path)
            connection = sqlite3.connect(str(db_path))
            columns = [row[1] for row in connection.execute("PRAGMA table_info(history)")]
            connection.close()
            self.assertIn("day", columns)

            store = UserStore("tester", db_path=db_path)
            store.create()
            rows = [{"일시": "2026-11-26T09:00:00+09:00", "구분": "암기", "단어": "apple", "방향": "",
                     "유형": "", "결과": "열람", "입력값": "", "정답": "", "일차": 3}]
            store.append_history(rows)
            self.assertEqual(store.read_history(), rows)


if __name__ == "__main__":
    unittest.main()
