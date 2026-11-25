#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 웹 로그인 함수 단위 테스트: 비밀번호 해시, 세션 토큰 서명·만료, 세션 키 준비
# 파일 위치: tests/test_auth_unit.py

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import auth  # noqa: E402


class PasswordHashTests(unittest.TestCase):
    def test_hash_is_not_plain_text_and_verifies(self):
        stored = auth.hash_password("secret-pw-1")
        self.assertNotIn("secret-pw-1", stored)
        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.assertTrue(auth.verify_password("secret-pw-1", stored))
        self.assertFalse(auth.verify_password("secret-pw-2", stored))

    def test_same_password_gets_different_salt(self):
        self.assertNotEqual(auth.hash_password("same-pass"), auth.hash_password("same-pass"))

    def test_missing_or_broken_hash_never_verifies(self):
        self.assertFalse(auth.verify_password("anything", None))
        self.assertFalse(auth.verify_password("anything", ""))
        self.assertFalse(auth.verify_password("anything", "not-a-hash"))
        self.assertFalse(auth.verify_password("anything", "md5$1$00$00"))

    def test_password_rules(self):
        self.assertIsNotNone(auth.password_problem("short"))
        self.assertIsNotNone(auth.password_problem("x" * (auth.MAX_PASSWORD_LENGTH + 1)))
        self.assertIsNone(auth.password_problem("long-enough"))


class SessionTokenTests(unittest.TestCase):
    secret = b"unit-test-secret"

    def test_token_round_trip(self):
        token = auth.make_session_token("학생1", self.secret, now=1000)
        self.assertEqual(auth.read_session_token(token, self.secret, now=1001), "학생1")

    def test_expired_token_is_rejected(self):
        token = auth.make_session_token("amy", self.secret, now=1000)
        after_expiry = 1000 + auth.SESSION_SECONDS + 1
        self.assertIsNone(auth.read_session_token(token, self.secret, now=after_expiry))

    def test_tampered_token_is_rejected(self):
        token = auth.make_session_token("amy", self.secret, now=1000)
        payload, signature = token.rsplit(".", 1)
        forged_payload = auth.make_session_token("bob", self.secret, now=1000).rsplit(".", 1)[0]
        self.assertIsNone(auth.read_session_token(f"{forged_payload}.{signature}", self.secret, now=1001))
        changed_last = "0" if token[-1] != "0" else "1"
        self.assertIsNone(auth.read_session_token(token[:-1] + changed_last, self.secret, now=1001))

    def test_token_from_other_secret_is_rejected(self):
        token = auth.make_session_token("amy", b"other-secret", now=1000)
        self.assertIsNone(auth.read_session_token(token, self.secret, now=1001))

    def test_empty_or_garbage_cookie_is_rejected(self):
        self.assertIsNone(auth.read_session_token(None, self.secret))
        self.assertIsNone(auth.read_session_token("", self.secret))
        self.assertIsNone(auth.read_session_token("no-dot-here", self.secret))
        self.assertIsNone(auth.read_session_token("가.나", self.secret))


class SecretKeyTests(unittest.TestCase):
    def test_environment_secret_is_used(self):
        with mock.patch.dict(os.environ, {"SECRET_KEY": "from-env"}):
            self.assertEqual(auth.load_secret_key(), b"from-env")

    def test_missing_secret_is_random_per_start(self):
        with mock.patch.dict(os.environ, {"SECRET_KEY": "   "}):
            first = auth.load_secret_key()
            second = auth.load_secret_key()
        self.assertGreaterEqual(len(first), 32)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
