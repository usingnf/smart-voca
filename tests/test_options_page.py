#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - 클로드 스마트 보카 - 옵션 화면의 온라인 검색 on/off와 설정 보존(인증키·창 크기) 테스트
# 파일 위치: tests/test_options_page.py

import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from settings import AppSettings  # noqa: E402

APP = QApplication.instance() or QApplication([])


class OptionsOnlineToggleTest(unittest.TestCase):
    def setUp(self):
        from ui.options_page import OptionsPage
        self.base = AppSettings(krdict_api_key="KEY123", window_width=1000, window_height=700)
        self.page = OptionsPage(self.base)

    def test_online_is_on_by_default(self):
        self.assertTrue(AppSettings().online_lookup_enabled)
        self.assertTrue(self.page.online_check.isChecked())

    def test_unchecking_turns_online_off_and_keeps_key_and_window_size(self):
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.online_check.setChecked(False)
        self.assertTrue(received)
        changed = received[-1]
        self.assertFalse(changed.online_lookup_enabled)
        self.assertEqual(changed.krdict_api_key, "KEY123")
        self.assertEqual((changed.window_width, changed.window_height), (1000, 700))

    def test_changing_other_option_keeps_key(self):
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.font_spin.setValue(self.page.font_spin.value() + 1)
        self.assertEqual(received[-1].krdict_api_key, "KEY123")

    def test_restore_defaults_keeps_key_and_resets_online_toggle(self):
        self.page.online_check.setChecked(False)
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.restore_defaults()
        restored = received[-1]
        self.assertEqual(restored.krdict_api_key, "KEY123")
        self.assertTrue(restored.online_lookup_enabled)
        self.assertTrue(self.page.online_check.isChecked())

    def test_loading_settings_sets_checkbox(self):
        self.page.load_values(replace(self.base, online_lookup_enabled=False))
        self.assertFalse(self.page.online_check.isChecked())

    def test_current_key_is_shown_in_input(self):
        self.assertEqual(self.page.key_input.text(), "KEY123")

    def test_show_checkbox_reveals_and_hides_key(self):
        from PyQt6.QtWidgets import QLineEdit
        self.page.key_show_check.setChecked(True)
        self.assertEqual(self.page.key_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.page.key_show_check.setChecked(False)
        self.assertEqual(self.page.key_input.echoMode(), QLineEdit.EchoMode.Password)

    def test_valid_key_is_saved_and_emitted(self):
        valid_key = "0123456789ABCDEF0123456789ABCDEF"
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.key_input.setText(f"  {valid_key}  ")
        self.page.save_key()
        self.assertEqual(received[-1].krdict_api_key, valid_key)
        self.assertEqual(received[-1].window_width, 1000)

    def test_invalid_key_is_rejected_without_saving(self):
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.key_input.setText("too-short")
        self.page.save_key()
        self.assertEqual(received, [])
        self.assertIn("32자리", self.page.key_status_label.text())

    def test_empty_input_clears_key(self):
        received = []
        self.page.settings_changed.connect(received.append)
        self.page.key_input.setText("")
        self.page.save_key()
        self.assertEqual(received[-1].krdict_api_key, "")


if __name__ == "__main__":
    unittest.main()
