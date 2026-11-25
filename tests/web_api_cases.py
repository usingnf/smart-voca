#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 웹 API 시나리오 테스트 (임시 데이터 폴더에서만 실행됨)
# 파일 위치: tests/web_api_cases.py
# 직접 실행하지 말고 tests/test_web_api.py가 SMARTVOCA_DATA_DIR을 지정해 실행한다.

import sys
import unittest
import uuid
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
WEB_DIR = TESTS_DIR.parent / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402

ALL_KINDS = ["단답형", "4지선다형", "OX형"]
ALL_POS = ["noun", "verb", "adj", "adv", "other"]
QUESTION_KEYS = {"index", "word", "direction", "kind", "prompt", "choices"}


class WebApiCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(create_app())

    def setUp(self):
        # 테스트마다 계정을 따로 만들어 서로의 과제·기록이 섞이지 않게 한다. 가입하면 그 계정으로 로그인된다.
        self.user = f"t{uuid.uuid4().hex[:10]}"
        self.password = "password-1"
        self.client.cookies.clear()
        self.assertEqual(self.register(self.user, self.password).status_code, 200)

    def register(self, name, password):
        return self.client.post("/api/auth/register", json={"username": name, "password": password})

    def login_as(self, name, password):
        self.client.cookies.clear()
        return self.client.post("/api/auth/login", json={"username": name, "password": password})

    def params(self, **extra):
        return {"username": self.user, **extra}

    def start_test_quiz(self, count=5, **overrides):
        body = {
            "username": self.user, "count": count, "kinds": ALL_KINDS,
            "pos_keys": ALL_POS, "direction": "영어→한글", "favorites_only": False,
            **overrides,
        }
        return self.client.post("/api/test/quiz", json=body)

    # ----- 계정 -----

    def test_foreign_host_header_is_rejected(self):
        response = self.client.get("/api/meta", headers={"host": "evil.example"})
        self.assertEqual(response.status_code, 400)

    def test_meta_reports_word_count_and_data_folder(self):
        data = self.client.get("/api/meta").json()
        self.assertEqual(data["word_count"], 4000)
        self.assertEqual(data["pos_order"], ALL_POS)

    def test_invalid_username_is_rejected(self):
        response = self.client.get("/api/history", params={"username": "../x"})
        self.assertEqual(response.status_code, 400)

    def test_anonymous_request_needs_login(self):
        self.client.cookies.clear()
        response = self.client.get("/api/history", params={"username": self.user})
        self.assertEqual(response.status_code, 401)

    def test_other_account_name_is_refused(self):
        response = self.client.get("/api/history", params={"username": "nobody"})
        self.assertEqual(response.status_code, 403)

    def test_login_logout_cycle(self):
        self.assertEqual(self.login_as(self.user, "wrong-password").status_code, 401)
        self.assertEqual(self.login_as(self.user, self.password).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").json()["username"], self.user)
        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_duplicate_register_and_short_password_are_rejected(self):
        self.client.cookies.clear()
        self.assertEqual(self.register(self.user, "another-pw").status_code, 409)
        self.assertEqual(self.register("shortpw_user", "short").status_code, 400)

    def test_private_account_is_hidden_from_others(self):
        self.register("viewer" + self.user[-6:], "password-2")
        listed = [item["username"] for item in self.client.get("/api/community/users").json()]
        self.assertNotIn(self.user, listed)
        self.assertEqual(self.client.get(f"/api/community/users/{self.user}").status_code, 404)

    def test_guest_login_creates_private_account(self):
        self.client.cookies.clear()
        guest = self.client.post("/api/auth/guest").json()
        self.assertTrue(guest["username"].startswith("guest"))
        self.assertTrue(guest["is_guest"])
        self.assertEqual(self.client.get("/api/auth/me").json()["username"], guest["username"])
        self.assertEqual(self.client.put("/api/auth/visibility", json={"is_public": True}).status_code, 403)
        # 게스트 이름으로 비밀번호 로그인과 가입은 할 수 없다
        self.assertEqual(self.login_as(guest["username"], "password-1").status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.register(guest["username"], "password-1").status_code, 409)

    def test_guest_accounts_are_not_listed_publicly(self):
        self.client.cookies.clear()
        guest = self.client.post("/api/auth/guest").json()["username"]
        self.register("viewer" + self.user[-6:], "password-2")
        listed = [item["username"] for item in self.client.get("/api/community/users").json()]
        self.assertNotIn(guest, listed)

    def test_public_account_is_visible_read_only(self):
        self.client.put("/api/auth/visibility", json={"is_public": True})
        self.register("viewer" + self.user[-6:], "password-2")
        listed = self.client.get("/api/community/users").json()
        mine = [item for item in listed if item["username"] == self.user]
        self.assertEqual(len(mine), 1)
        self.assertFalse(mine[0]["is_me"])
        detail = self.client.get(f"/api/community/users/{self.user}")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue({"day", "memorized", "total", "test_accuracy"} <= set(detail.json()))
        self.assertEqual(self.client.delete(f"/api/community/users/{self.user}").status_code, 405)
        self.assertNotIn("meanings", str(detail.json()))

    # ----- 단어 -----

    def test_search_by_english_and_meaning(self):
        english = self.client.get("/api/words/search", params=self.params(q="apple", mode="english")).json()
        self.assertEqual(english[0]["word"], "apple")
        meaning = self.client.get("/api/words/search", params=self.params(q="사과", mode="meaning")).json()
        self.assertTrue(meaning)

    def test_add_word_then_duplicate_merges(self):
        # 기본 단어장에 없는 가짜 단어를 써서 '새 단어'와 '중복'을 확실히 구분한다.
        first = self.client.post("/api/words", json={
            "username": self.user, "word": "Zorblang", "pos": "noun", "meanings": ["석영"],
        }).json()
        self.assertFalse(first["merged"])
        second = self.client.post("/api/words", json={
            "username": self.user, "word": "zorblang", "pos": "noun", "meanings": ["수정"],
        }).json()
        self.assertTrue(second["merged"])

    def test_invalid_word_and_empty_meaning_are_rejected(self):
        bad_word = self.client.post("/api/words", json={
            "username": self.user, "word": "123", "pos": "noun", "meanings": ["뜻"],
        })
        self.assertEqual(bad_word.status_code, 400)
        no_meaning = self.client.post("/api/words", json={
            "username": self.user, "word": "lamp", "pos": "noun", "meanings": [" "],
        })
        self.assertEqual(no_meaning.status_code, 400)

    def test_custom_word_can_be_edited_and_deleted_but_base_word_cannot(self):
        self.client.post("/api/words", json={
            "username": self.user, "word": "pebble", "pos": "noun", "meanings": ["조약돌"],
        })
        edited = self.client.put("/api/words/pebble", json={
            "username": self.user, "pos": "noun", "meanings": ["작은 돌"],
        })
        self.assertEqual(edited.status_code, 200)
        base = self.client.put("/api/words/apple", json={
            "username": self.user, "pos": "noun", "meanings": ["바꿈"],
        })
        self.assertEqual(base.status_code, 400)
        deleted = self.client.delete("/api/words/pebble", params=self.params())
        self.assertEqual(deleted.status_code, 200)

    def test_favorite_toggle(self):
        on = self.client.post("/api/favorites/apple", json={"username": self.user}).json()["favorite"]
        off = self.client.post("/api/favorites/apple", json={"username": self.user}).json()["favorite"]
        self.assertTrue(on)
        self.assertFalse(off)

    # ----- 암기 -----

    def test_memorize_open_records_history_once(self):
        self.client.post("/api/memorize/open", json={"username": self.user, "word": "apple"})
        self.client.post("/api/memorize/open", json={"username": self.user, "word": "apple"})
        history = self.client.get("/api/history", params=self.params()).json()
        rows = [row for row in history if row["단어"] == "apple" and row["구분"] == "암기"]
        self.assertEqual(len(rows), 1)

    def test_memorize_next_returns_word_without_answer_fields(self):
        data = self.client.get("/api/memorize/next", params=self.params()).json()
        self.assertIn("word", data["word"])
        self.assertIn("meanings", data["word"])

    # ----- 시험 -----

    def test_test_quiz_hides_answers(self):
        quiz = self.start_test_quiz(count=5).json()
        self.assertEqual(quiz["total"], 5)
        for question in quiz["questions"]:
            self.assertEqual(set(question.keys()), QUESTION_KEYS)

    def test_test_quiz_rejects_bad_options(self):
        self.assertEqual(self.start_test_quiz(count=7).status_code, 400)
        self.assertEqual(self.start_test_quiz(kinds=["없는유형"]).status_code, 400)
        self.assertEqual(self.start_test_quiz(pos_keys=[]).status_code, 400)

    def test_grading_requires_matching_answer_count(self):
        quiz = self.start_test_quiz(count=5).json()
        response = self.client.post(f"/api/quiz/{quiz['quiz_id']}/grade", json={"answers": ["x"]})
        self.assertEqual(response.status_code, 400)

    def test_wrong_answers_are_recorded_and_offer_wrong_retest(self):
        quiz = self.start_test_quiz(count=5).json()
        graded = self.client.post(
            f"/api/quiz/{quiz['quiz_id']}/grade", json={"answers": ["???"] * 5},
        ).json()
        self.assertEqual(graded["score"], 0.0)
        self.assertIsNone(graded["passed"])
        retest = self.client.post("/api/test/wrong", json={
            "username": self.user, "kinds": ALL_KINDS, "direction": "영어→한글",
        })
        self.assertEqual(retest.status_code, 200)
        self.assertEqual(retest.json()["title"], "오답 재시험")

    def test_grade_unknown_quiz_is_not_found(self):
        response = self.client.post("/api/quiz/no-such-id/grade", json={"answers": []})
        self.assertEqual(response.status_code, 404)

    # ----- 과제 -----

    def test_assignment_has_twenty_words_and_quiz_starts(self):
        assignment = self.client.get("/api/assignment", params=self.params()).json()
        self.assertEqual(len(assignment["words"]), 20)
        self.assertTrue(assignment["pending"])
        quiz = self.client.post("/api/assignment/quiz", json={"username": self.user})
        self.assertEqual(quiz.status_code, 200)
        self.assertEqual(quiz.json()["total"], 20)

    def test_abort_marks_assignment_missed(self):
        quiz = self.client.post("/api/assignment/quiz", json={"username": self.user}).json()
        self.client.post(f"/api/quiz/{quiz['quiz_id']}/abort")
        after = self.client.get("/api/assignment", params=self.params()).json()
        self.assertEqual(after["status"], "missed")
        self.assertFalse(after["pending"])

    def test_finished_assignment_cannot_start_again(self):
        quiz = self.client.post("/api/assignment/quiz", json={"username": self.user}).json()
        self.client.post(f"/api/quiz/{quiz['quiz_id']}/abort")
        response = self.client.post("/api/assignment/quiz", json={"username": self.user})
        self.assertEqual(response.status_code, 400)

    # ----- 보고서, 이력, 옵션 -----

    def test_report_accepts_presets_and_rejects_bad_custom_range(self):
        ok = self.client.get("/api/report", params=self.params(period="최근 7일")).json()
        self.assertEqual(ok["period"], "최근 7일")
        self.assertEqual(len(ok["daily"]), 14)
        bad = self.client.get("/api/report", params=self.params(
            period="기간 선택", start="2026-12-02", end="2026-12-01"))
        self.assertEqual(bad.status_code, 400)

    def test_history_export_returns_csv_after_records(self):
        self.assertEqual(self.client.get("/api/history/export", params=self.params()).status_code, 404)
        self.client.post("/api/memorize/open", json={"username": self.user, "word": "apple"})
        response = self.client.get("/api/history/export", params=self.params())
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])

    def test_settings_update_and_api_key_is_not_returned(self):
        self.client.put("/api/settings", json={"theme": "어둡게", "krdict_api_key": "SECRET-KEY"})
        data = self.client.get("/api/settings").json()
        self.assertEqual(data["theme"], "어둡게")
        self.assertTrue(data["krdict_api_key_set"])
        self.assertNotIn("krdict_api_key", data)
        self.assertNotIn("SECRET-KEY", str(data))

    def test_online_search_without_key_makes_no_network_call(self):
        self.client.put("/api/settings", json={"krdict_api_key": "", "online_lookup_enabled": True})
        data = self.client.get("/api/online-search", params=self.params(q="사과")).json()
        self.assertEqual(data["results"], [])
        self.assertIn("인증키", data["message"])

    def test_reset_keeps_custom_words(self):
        self.client.post("/api/words", json={
            "username": self.user, "word": "lantern", "pos": "noun", "meanings": ["등불"],
        })
        self.client.post(f"/api/users/{self.user}/reset")
        self.assertEqual(self.client.get("/api/words/lantern", params=self.params()).status_code, 200)


    # ----- 가져오기·진도·가중 출제 (v1.2) -----

    def test_import_words_adds_new_and_skips_existing(self):
        # 머리글 BOM, 기존 단어(abacus), 같은 파일 안 중복(plimbox), 형식 오류(숫자) 한 번에 확인
        text = "﻿영단어,뜻\nplimbox,상자\nabacus,수판\nplimbox,중복\n123,숫자\n"
        result = self.client.post("/api/words/import", json={"username": self.user, "text": text}).json()
        self.assertEqual((result["added"], result["skipped"], result["invalid"]), (1, 2, 1))
        self.assertEqual(result["errors"][0]["line"], 5)
        self.assertEqual(self.client.get("/api/words/plimbox", params=self.params()).status_code, 200)

    def test_memorize_today_only_uses_assignment_words(self):
        assignment = self.client.get("/api/assignment", params=self.params()).json()
        today_words = {word["word"] for word in assignment["words"]}
        for _ in range(5):
            data = self.client.get("/api/memorize/next", params=self.params(today_only=True)).json()
            self.assertIn(data["word"]["word"], today_words)

    def test_assignment_reports_day_and_progress(self):
        assignment = self.client.get("/api/assignment", params=self.params()).json()
        self.assertEqual(assignment["day_number"], 1)
        self.assertEqual(assignment["memorized_count"], 0)
        self.assertGreater(assignment["total_count"], 0)
        self.client.post("/api/memorize/open", json={
            "username": self.user, "word": assignment["words"][0]["word"],
        })
        after = self.client.get("/api/assignment", params=self.params()).json()
        self.assertEqual(after["memorized_count"], 1)


if __name__ == "__main__":
    unittest.main()
