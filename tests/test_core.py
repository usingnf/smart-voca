#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 채점, 문항 구성, 과제 로직, 보고서 집계, 설정 단위 테스트
# 파일 위치: tests/test_core.py

import random
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from config import STATUS_COMPLETED, STATUS_MISSED, STATUS_PENDING  # noqa: E402
from daily import complete_assignment, create_today_assignment  # noqa: E402
from quiz import (  # noqa: E402
    DIRECTION_EN_TO_KO,
    DIRECTION_MIXED,
    KIND_CHOICE,
    KIND_OX,
    KIND_SHORT,
    build_questions,
    distribute_counts,
    grade_answers,
    normalize_answer,
    score_of,
)
from report import PERIOD_LAST_7, build_summary, period_range, top_wrong_words  # noqa: E402
from settings import AppSettings  # noqa: E402
from user_store import UserStore, normalize_username  # noqa: E402
from vocab import WordEntry  # noqa: E402


def make_pool(count, pos="noun"):
    """테스트용 단어 풀. 단어는 w00, w01 ... 이고 뜻은 '뜻00' 형식이다."""
    pool = {}
    for index in range(count):
        word = f"w{index:02d}"
        pool[word] = WordEntry(word=word, pos=pos, meanings=[f"뜻{index:02d}"])
    return pool


class NormalizeTests(unittest.TestCase):
    def test_case_and_spaces_are_ignored(self):
        self.assertEqual(normalize_answer(" Apple Pie "), normalize_answer("applepie"))

    def test_username_rules(self):
        self.assertEqual(normalize_username(" Kim01 "), "kim01")
        self.assertEqual(normalize_username("김철수"), "김철수")
        self.assertIsNone(normalize_username("bad name!"))
        self.assertIsNone(normalize_username("a" * 21))


class DistributionTests(unittest.TestCase):
    def test_remainder_goes_to_front_slots(self):
        self.assertEqual(distribute_counts(20, 3), [7, 7, 6])
        self.assertEqual(distribute_counts(7, 3), [3, 2, 2])

    def test_review_count_stays_in_range(self):
        from daily import choose_review_count
        rng = random.Random(1)
        values = {choose_review_count(rng) for _ in range(500)}
        self.assertTrue(values <= set(range(2, 11)))
        self.assertIn(2, values)
        self.assertIn(10, values)


class QuestionTests(unittest.TestCase):
    def test_question_counts_and_ox_balance(self):
        rng = random.Random(7)
        pool = make_pool(40)
        targets = list(pool.values())[:20]
        questions = build_questions(targets, pool, DIRECTION_MIXED,
                                    [KIND_SHORT, KIND_CHOICE, KIND_OX], rng)
        self.assertEqual(len(questions), 20)
        kinds = [question.kind for question in questions]
        self.assertEqual(kinds.count(KIND_SHORT), 7)
        self.assertEqual(kinds.count(KIND_CHOICE), 7)
        self.assertEqual(kinds.count(KIND_OX), 6)
        directions = [question.direction for question in questions]
        self.assertEqual(directions.count(DIRECTION_EN_TO_KO), 10)

    def test_choice_distractors_never_share_meaning(self):
        rng = random.Random(3)
        pool = make_pool(10)
        pool["w00"].meanings.append("공유뜻")
        pool["w01"].meanings.append("공유뜻")
        targets = [pool["w00"]]
        question = build_questions(targets, pool, DIRECTION_EN_TO_KO, [KIND_CHOICE], rng)[0]
        self.assertEqual(len(question.choices), 4)
        self.assertNotIn("뜻01", question.choices)
        self.assertNotIn("공유뜻", question.choices)

    def test_multiple_meanings_are_all_accepted(self):
        pool = {"fed": WordEntry("fed", "noun", ["연방", "연합"])}
        question = build_questions([pool["fed"]], pool, DIRECTION_EN_TO_KO, [KIND_SHORT],
                                   random.Random(0))[0]
        results = grade_answers([question], ["연합"])
        self.assertTrue(results[0].is_correct)
        self.assertEqual(score_of(results), 1.0)

    def test_grading_ignores_case_and_spaces(self):
        pool = {"apple": WordEntry("apple", "noun", ["사과"])}
        question = build_questions([pool["apple"]], pool, "한글→영어", [KIND_SHORT],
                                   random.Random(0))[0]
        self.assertTrue(grade_answers([question], [" Apple "])[0].is_correct)


class AssignmentTests(unittest.TestCase):
    def test_assignment_has_twenty_unique_words(self):
        state = {"assignments": [], "queue": [], "stats": {}, "memorized": {}}
        pool = make_pool(60)
        assignment = create_today_assignment(state, date(2026, 10, 21), pool, random.Random(5))
        self.assertEqual(len(assignment["words"]), 20)
        self.assertEqual(len(set(assignment["words"])), 20)
        self.assertLessEqual(len(assignment["review"]), 10)
        self.assertEqual(len(assignment["review"]) + len(assignment["new"]), 20)

    def test_missed_assignment_carries_over(self):
        state = {"assignments": [], "queue": [], "stats": {}, "memorized": {}}
        pool = make_pool(60)
        rng = random.Random(9)
        first = create_today_assignment(state, date(2026, 10, 21), pool, rng)
        second = create_today_assignment(state, date(2026, 10, 22), pool, rng)
        self.assertEqual(first["status"], STATUS_MISSED)
        self.assertEqual(second["status"], STATUS_PENDING)
        carried = [word for word in first["words"] if word in second["words"]]
        self.assertTrue(carried, "미이수 단어가 다음 날 과제에 이어져야 합니다")
        self.assertLessEqual(len(second["review"]), 10)

    def test_same_day_returns_same_assignment(self):
        state = {"assignments": [], "queue": [], "stats": {}, "memorized": {}}
        pool = make_pool(30)
        rng = random.Random(2)
        first = create_today_assignment(state, date(2026, 10, 21), pool, rng)
        again = create_today_assignment(state, date(2026, 10, 21), pool, rng)
        self.assertIs(first, again)
        self.assertEqual(len(state["assignments"]), 1)

    def test_pass_threshold_is_eighty_percent(self):
        assignment = {"status": STATUS_PENDING, "score": None}
        self.assertTrue(complete_assignment(assignment, 16 / 20))
        self.assertEqual(assignment["status"], STATUS_COMPLETED)
        failing = {"status": STATUS_PENDING, "score": None}
        self.assertFalse(complete_assignment(failing, 15 / 20))
        self.assertEqual(failing["status"], STATUS_PENDING)


class ReportTests(unittest.TestCase):
    def test_top_wrong_words_order(self):
        rows = [
            {"구분": "시험", "단어": "a", "결과": "오답"},
            {"구분": "시험", "단어": "a", "결과": "정답"},
            {"구분": "과제시험", "단어": "b", "결과": "오답"},
            {"구분": "시험", "단어": "c", "결과": "정답"},
            {"구분": "암기", "단어": "d", "결과": "열람"},
        ]
        ranked = top_wrong_words(rows)
        self.assertEqual([item[0] for item in ranked], ["b", "a", "c"])
        self.assertEqual(ranked[1][3], 0.5)

    def test_period_last_seven_days(self):
        start, end = period_range(PERIOD_LAST_7, date(2026, 10, 21))
        self.assertEqual(start, date(2026, 10, 15))
        self.assertEqual(end, date(2026, 10, 21))

    def test_summary_completion_rate(self):
        today = date(2026, 10, 21)
        assignments = [
            {"date": (today - timedelta(days=2)).isoformat(), "status": STATUS_COMPLETED},
            {"date": (today - timedelta(days=1)).isoformat(), "status": STATUS_MISSED},
            {"date": today.isoformat(), "status": STATUS_PENDING},
        ]
        summary = build_summary([], assignments, None, None)
        self.assertEqual(summary["completion_rate"], 0.5)


class StoreTests(unittest.TestCase):
    def test_reset_keeps_custom_words(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserStore("tester", base_dir=temp_dir)
            store.create()
            store.save_custom_words({"apple": WordEntry("apple", "noun", ["사과"], source="사용자 입력")})
            store.append_history([{"일시": "2026-10-21T10:00:00+09:00", "구분": "시험", "단어": "apple",
                                   "방향": "", "유형": "", "결과": "정답", "입력값": "", "정답": ""}])
            store.reset()
            self.assertEqual(store.read_history(), [])
            self.assertIn("apple", store.load_custom_words())


class PartOfSpeechTests(unittest.TestCase):
    def test_multi_pos_entries_match_each_selected_pos(self):
        from vocab import filter_by_pos
        pool = {
            "run": WordEntry("run", "noun, verb", ["달리기", "달리다"]),
            "quick": WordEntry("quick", "adj", ["빠른"]),
            "hello": WordEntry("hello", "", ["안녕"]),
            "name": WordEntry("name", "name", ["이름"]),
        }
        self.assertEqual(set(filter_by_pos(pool, ["verb"])), {"run"})
        self.assertEqual(set(filter_by_pos(pool, ["adj"])), {"quick"})
        self.assertEqual(set(filter_by_pos(pool, ["other"])), {"hello", "name"})

    def test_distractors_prefer_overlapping_pos(self):
        pool = {
            "run": WordEntry("run", "noun, verb", ["달리기"]),
            "walk": WordEntry("walk", "verb", ["걷다"]),
            "table": WordEntry("table", "noun", ["탁자"]),
            "jump": WordEntry("jump", "verb", ["뛰다"]),
            "quick": WordEntry("quick", "adj", ["빠른"]),
            "happy": WordEntry("happy", "adj", ["행복한"]),
        }
        rng = random.Random(4)
        from quiz import pick_distractors
        picked = pick_distractors(pool["run"], pool, DIRECTION_EN_TO_KO, rng)
        self.assertEqual({entry.word for entry in picked}, {"walk", "table", "jump"})


class SettingsTests(unittest.TestCase):
    def test_out_of_range_values_are_corrected(self):
        settings = AppSettings(theme="이상함", font_size=40, exam_count=23, exam_direction="?").sanitized()
        self.assertEqual(settings.theme, "밝게")
        self.assertEqual(settings.font_size, 16)
        self.assertEqual(settings.exam_count, 20)
        self.assertEqual(settings.exam_direction, DIRECTION_EN_TO_KO)


if __name__ == "__main__":
    unittest.main()
