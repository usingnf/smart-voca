#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 클로드 스마트 보카 - 처리되지 않은 오류 로그 기록과 창 없이 동작하는 처리기 테스트
# 파일 위치: tests/test_crash_log.py

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from crash_log import make_uncaught_handler, write_error_log  # noqa: E402


class CrashLogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.temp_dir.name) / "sub" / "error.log"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _raise_and_handle(self, handler):
        try:
            raise ValueError("테스트 오류")
        except ValueError:
            handler(*sys.exc_info())

    def test_handler_writes_exception_to_log_without_dialog(self):
        handler = make_uncaught_handler(log_path=self.log_path, show_dialog=False)
        self._raise_and_handle(handler)
        content = self.log_path.read_text(encoding="utf-8")
        self.assertIn("ValueError", content)
        self.assertIn("테스트 오류", content)

    def test_log_appends_entries(self):
        self.assertTrue(write_error_log("첫 번째\n", self.log_path))
        self.assertTrue(write_error_log("두 번째\n", self.log_path))
        content = self.log_path.read_text(encoding="utf-8")
        self.assertIn("첫 번째", content)
        self.assertIn("두 번째", content)

    def test_write_failure_returns_false_instead_of_raising(self):
        # 파일 이름 자리에 기존 폴더를 두면 쓸 수 없으므로 실패해야 한다.
        blocked = Path(self.temp_dir.name) / "blocked"
        blocked.mkdir()
        self.assertFalse(write_error_log("내용", blocked))

    def test_keyboard_interrupt_is_not_logged(self):
        handler = make_uncaught_handler(log_path=self.log_path, show_dialog=False)
        original = sys.__excepthook__
        calls = []
        sys.__excepthook__ = lambda *args: calls.append(args)
        try:
            try:
                raise KeyboardInterrupt()
            except KeyboardInterrupt:
                handler(*sys.exc_info())
        finally:
            sys.__excepthook__ = original
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.log_path.exists())


if __name__ == "__main__":
    unittest.main()
