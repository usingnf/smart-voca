#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 클로드 스마트 보카 - 중도 종료 안내, 온라인 오류 캐시, 암기 즐겨찾기 안내, 암기 이력 중복, 중복 제출 방지 테스트
# 파일 위치: tests/test_ui_fixes.py

import os
import random
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from quiz import DIRECTION_EN_TO_KO, KIND_SHORT, build_questions  # noqa: E402
from vocab import WordEntry  # noqa: E402

APP = QApplication.instance() or QApplication([])


def make_pool(count):
    pool = {}
    for index in range(count):
        word = f"w{index:02d}"
        pool[word] = WordEntry(word=word, pos="noun", meanings=[f"뜻{index:02d}"])
    return pool


class FakeStore:
    """디스크에 쓰지 않고 호출 내용만 기록하는 저장소."""

    def __init__(self):
        self.saved_states = []
        self.history_rows = []

    def save_state(self, state):
        self.saved_states.append(state)

    def append_history(self, rows):
        self.history_rows.extend(rows)


class FakeSession:
    """화면이 쓰는 최소한의 세션 인터페이스."""

    def __init__(self, pool, favorites=()):
        self.pool = pool
        self.favorites = set(favorites)
        self.rng = random.Random(1)
        self.custom = {}
        self.memorized = []

    def is_favorite(self, word):
        return word in self.favorites

    def favorite_pool(self):
        return {word: entry for word, entry in self.pool.items() if word in self.favorites}

    def wrong_words(self):
        return []

    def exists_word(self, word):
        return word in self.pool

    def record_memorize(self, word):
        self.memorized.append(word)


class RecordMemorizeTests(unittest.TestCase):
    def setUp(self):
        from session import UserSession
        self.session = UserSession.__new__(UserSession)
        self.session.state = {"memorized": {}}
        self.session.store = FakeStore()

    def test_same_word_same_day_adds_history_only_once(self):
        self.session.record_memorize("apple")
        self.session.record_memorize("apple")
        self.session.record_memorize("apple")
        self.assertEqual(len(self.session.store.history_rows), 1)
        self.assertEqual(sum(len(words) for words in self.session.state["memorized"].values()), 1)

    def test_different_words_are_each_recorded(self):
        self.session.record_memorize("apple")
        self.session.record_memorize("pear")
        self.assertEqual([row["단어"] for row in self.session.store.history_rows], ["apple", "pear"])


class SearchOnlineCacheTests(unittest.TestCase):
    def setUp(self):
        from ui.study_pages import SearchPage
        self.page = SearchPage(FakeSession(make_pool(3)))
        self.page.query_input.setText("사과")

    def test_failed_lookup_is_not_cached(self):
        self.page.on_online_lookup_done("사과", [], "시간 초과")
        self.assertNotIn("사과", self.page.online_cache)
        self.assertIn("시간 초과", self.page.online_label.text())

    def test_successful_lookup_is_cached(self):
        self.page.on_online_lookup_done("사과", [], "")
        self.assertIn("사과", self.page.online_cache)

    def test_shutdown_without_workers_is_safe(self):
        self.page.shutdown()
        self.assertEqual(self.page.online_workers, [])


class MemorizeFavoriteNoticeTests(unittest.TestCase):
    def test_notice_shown_when_no_favorites_fall_back_to_all_words(self):
        from ui.study_pages import MemorizePage
        page = MemorizePage(FakeSession(make_pool(3)))
        page.favorites_only.setChecked(True)
        self.assertIn("즐겨찾기 단어가 없어", page.notice_label.text())

    def test_notice_cleared_when_favorites_exist(self):
        from ui.study_pages import MemorizePage
        page = MemorizePage(FakeSession(make_pool(3), favorites=["w01"]))
        page.favorites_only.setChecked(True)
        self.assertEqual(page.notice_label.text(), "")
        self.assertEqual(page.current.word, "w01")


class QuizDialogTests(unittest.TestCase):
    def setUp(self):
        from ui.quiz_dialog import ANSWER_COOLDOWN_MS, DEFAULT_ABORT_MESSAGE, QuizDialog
        self.default_message = DEFAULT_ABORT_MESSAGE
        self.cooldown_ms = ANSWER_COOLDOWN_MS
        pool = make_pool(5)
        targets = [pool["w00"], pool["w01"], pool["w02"]]
        questions = build_questions(targets, pool, DIRECTION_EN_TO_KO, [KIND_SHORT], random.Random(2))
        self.dialog = QuizDialog(questions, "테스트")
        self.QuizDialog = QuizDialog
        self.questions = questions

    def test_quick_second_submit_is_ignored_as_double_click(self):
        self.dialog.submit("a")
        self.dialog.submit("b")  # 더블클릭으로 다음 문항이 두 번 넘어가지 않아야 함
        self.assertEqual(self.dialog.answers, ["a"])

    def test_answer_is_accepted_after_cooldown(self):
        self.dialog.submit("a")
        time.sleep((self.cooldown_ms + 100) / 1000)
        self.dialog.submit("b")
        self.assertEqual(self.dialog.answers, ["a", "b"])

    def test_default_abort_message_is_used_without_custom_text(self):
        self.assertEqual(self.dialog.abort_message, self.default_message)

    def test_custom_abort_message_is_kept(self):
        dialog = self.QuizDialog(self.questions, "테스트", abort_message="사용자 문구")
        self.assertEqual(dialog.abort_message, "사용자 문구")


class SettingsSanitizeTests(unittest.TestCase):
    def test_unknown_exam_kinds_and_positions_fall_back_to_all(self):
        from settings import EXAM_KIND_CHOICES, AppSettings
        from config import POS_DEFAULT_ORDER
        cleaned = AppSettings(exam_kinds=["없는 유형"], exam_pos_keys=["bogus"]).sanitized()
        self.assertEqual(cleaned.exam_kinds, EXAM_KIND_CHOICES)
        self.assertEqual(cleaned.exam_pos_keys, POS_DEFAULT_ORDER)

    def test_valid_selection_is_kept_in_order(self):
        from quiz import KIND_OX, KIND_SHORT
        from settings import AppSettings
        cleaned = AppSettings(exam_kinds=[KIND_OX, KIND_SHORT], exam_favorites_only=True).sanitized()
        self.assertEqual(cleaned.exam_kinds, [KIND_OX, KIND_SHORT])
        self.assertTrue(cleaned.exam_favorites_only)


class QuizRetestButtonTests(unittest.TestCase):
    def _answer_all_wrong(self, dialog):
        for _ in dialog.questions:
            dialog.submit("틀린 답 zzz")
            time.sleep((self.cooldown_ms + 50) / 1000)

    def setUp(self):
        from ui.quiz_dialog import ANSWER_COOLDOWN_MS, QuizDialog
        self.cooldown_ms = ANSWER_COOLDOWN_MS
        self.QuizDialog = QuizDialog
        pool = make_pool(5)
        targets = [pool["w00"], pool["w01"], pool["w02"]]
        self.questions = build_questions(targets, pool, DIRECTION_EN_TO_KO, [KIND_SHORT], random.Random(3))

    def test_retest_button_hidden_when_not_allowed(self):
        dialog = self.QuizDialog(self.questions, "과제 시험")
        self._answer_all_wrong(dialog)
        self.assertTrue(dialog.retest_button.isHidden())
        self.assertFalse(dialog.retest_requested)

    def test_retest_button_shown_and_retest_collects_wrong_words(self):
        dialog = self.QuizDialog(self.questions, "시험", allow_retest=True)
        self._answer_all_wrong(dialog)
        self.assertFalse(dialog.retest_button.isHidden())
        self.assertEqual(dialog.wrong_words(), ["w00", "w01", "w02"])
        dialog.request_retest()
        self.assertTrue(dialog.retest_requested)


class TestPagePreferenceTests(unittest.TestCase):
    def setUp(self):
        from settings import AppSettings
        from ui.test_pages import TestPage
        self.page = TestPage(FakeSession(make_pool(3)))
        self.received = []
        self.page.preferences_changed.connect(self.received.append)
        self.AppSettings = AppSettings

    def test_apply_settings_sets_saved_selection_without_emitting(self):
        from quiz import KIND_OX
        self.page.apply_settings(self.AppSettings(exam_kinds=[KIND_OX], exam_favorites_only=True))
        self.assertEqual(self.page.selected_kinds(), [KIND_OX])
        self.assertTrue(self.page.favorites_check.isChecked())
        self.assertEqual(self.received, [])

    def test_user_change_emits_current_selection(self):
        self.page.favorites_check.setChecked(True)
        self.assertTrue(self.received)
        self.assertTrue(self.received[-1]["exam_favorites_only"])

    def test_last_type_cannot_be_unchecked(self):
        for check in self.page.type_checks:
            check.setChecked(False)
        self.assertEqual(len(self.page.selected_kinds()), 1)

    def test_last_position_cannot_be_unchecked(self):
        for check in self.page.pos_checks:
            check.setChecked(False)
        self.assertEqual(len(self.page.selected_pos_keys()), 1)


class AddWordDuplicateHintTests(unittest.TestCase):
    def setUp(self):
        from ui.study_pages import AddWordPage
        self.page = AddWordPage(FakeSession(make_pool(3)))

    def test_hint_shown_for_existing_word_while_typing(self):
        self.page.word_input.setText("W01")
        self.assertIn("이미 있는 단어", self.page.duplicate_hint.text())

    def test_hint_hidden_for_new_word(self):
        self.page.word_input.setText("brandnew")
        self.assertEqual(self.page.duplicate_hint.text(), "")


class MemorizeKeyboardTests(unittest.TestCase):
    def setUp(self):
        from ui.study_pages import MemorizePage
        self.session = FakeSession(make_pool(3))
        self.page = MemorizePage(self.session)

    def test_first_press_opens_answer_and_records_it(self):
        self.page.open_or_next()
        self.assertTrue(self.page._answer_shown)
        self.assertEqual(self.session.memorized, [self.page.current.word])

    def test_second_press_moves_to_next_word(self):
        self.page.open_or_next()
        self.page.open_or_next()
        self.assertFalse(self.page._answer_shown)
        self.assertEqual(self.page.answer_label.text(), "")


class MenuLayoutTests(unittest.TestCase):
    def test_every_page_index_appears_once(self):
        from ui.main_window import MENU_LAYOUT
        indices = [index for _label, index in MENU_LAYOUT if index is not None]
        self.assertEqual(sorted(indices), list(range(8)))


if __name__ == "__main__":
    unittest.main()
