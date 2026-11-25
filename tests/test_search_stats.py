#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 검색 함수(T-12)와 오답률·회차 갱신(T-14) 테스트
# 파일 위치: tests/test_search_stats.py

import random
import sys
import unittest
from collections import namedtuple
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from session import UserSession  # noqa: E402
from timeutil import kst_today  # noqa: E402
from vocab import WordEntry, search_by_english, search_by_meaning  # noqa: E402

QuizResult = namedtuple("QuizResult", "word direction kind user_answer expected_text is_correct")


def make_pool():
    entries = [
        WordEntry(word="apple", pos="noun", meanings=["사과"]),
        WordEntry(word="pear", pos="noun", meanings=["배"]),
        WordEntry(word="applet", pos="noun", meanings=["작은 사과 모양"]),
        WordEntry(word="snack", pos="noun", meanings=["간식", "사과 조각"]),
    ]
    return {entry.word: entry for entry in entries}


class SearchTests(unittest.TestCase):
    def test_english_search_ignores_case_and_spaces(self):
        found = search_by_english(make_pool(), " APPLE ")
        self.assertEqual([entry.word for entry in found], ["apple"])

    def test_english_search_without_match_is_empty(self):
        self.assertEqual(search_by_english(make_pool(), "appl"), [])

    def test_meaning_search_puts_exact_matches_first(self):
        found = [entry.word for entry in search_by_meaning(make_pool(), "사과")]
        self.assertEqual(found, ["apple", "applet", "snack"])

    def test_meaning_search_respects_limit(self):
        found = [entry.word for entry in search_by_meaning(make_pool(), "사과", limit=2)]
        self.assertEqual(found, ["apple", "applet"])

    def test_meaning_search_without_match_is_empty(self):
        self.assertEqual(search_by_meaning(make_pool(), "없는뜻"), [])


class FakeStore:
    def __init__(self):
        self.history_rows = []

    def append_history(self, rows):
        self.history_rows.extend(rows)


def make_session():
    session = UserSession.__new__(UserSession)
    session.state = {"stats": {}, "memorized": {}, "assignments": [], "queue": [], "favorites": []}
    session.store = FakeStore()
    session.rng = random.Random(1)
    session.save = lambda: None
    return session


class StatsUpdateTests(unittest.TestCase):
    def test_asked_wrong_and_last_asked_are_updated(self):
        session = make_session()
        session.record_results([
            QuizResult("apple", "영어→한글", "단답형", "x", "사과", False),
            QuizResult("apple", "영어→한글", "단답형", "사과", "사과", True),
            QuizResult("pear", "영어→한글", "OX형", "O", "배", True),
        ], "시험")
        apple = session.state["stats"]["apple"]
        self.assertEqual((apple["asked"], apple["wrong"]), (2, 1))
        self.assertEqual(session.state["stats"]["pear"]["asked"], 1)
        self.assertEqual(session.state["stats"]["pear"]["wrong"], 0)
        self.assertEqual(apple["last_asked"], kst_today().isoformat())

    def test_repeated_tests_accumulate_error_rate(self):
        session = make_session()
        session.record_results([QuizResult("apple", "영어→한글", "단답형", "x", "사과", False)], "시험")
        session.record_results([QuizResult("apple", "영어→한글", "단답형", "사과", "사과", True)], "시험")
        from daily import error_rate
        self.assertEqual(error_rate(session.state["stats"], "apple"), 0.5)

    def test_each_test_is_one_run_with_correct_count(self):
        session = make_session()
        session.record_results([
            QuizResult("apple", "영어→한글", "단답형", "사과", "사과", True),
            QuizResult("pear", "영어→한글", "단답형", "x", "배", False),
        ], "시험")
        session.record_results([QuizResult("apple", "영어→한글", "단답형", "사과", "사과", True)], "과제시험")
        runs = session.recent_runs(20)
        self.assertEqual([run["label"] for run in runs], ["1회", "2회"])
        self.assertEqual(runs[0]["rate"], 0.5)
        self.assertEqual(runs[1]["rate"], 1.0)
        self.assertEqual(runs[1]["kind"], "과제시험")


if __name__ == "__main__":
    unittest.main()
