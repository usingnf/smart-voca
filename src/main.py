#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 진입점. 계정 선택 → 메인 창 흐름과 계정 전환을 처리한다
# 파일 위치: src/main.py

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from config import APP_TITLE, VOCA_PATH
from session import UserSession
from settings import load_settings
from ui.login_dialog import LoginDialog
from ui.main_window import SESSION_END_SWITCH, MainWindow
from ui.theme import apply_app_font, apply_theme
from vocab import Vocabulary


class AppController:
    """계정 선택 창과 메인 창을 번갈아 띄운다. 계정 전환 시 로그인 창으로 돌아간다."""

    def __init__(self, app, vocabulary, settings):
        self.app = app
        self.vocabulary = vocabulary
        self.settings = settings
        self.window = None

    def show_login(self):
        """로그인 창을 띄운다. 취소하면 False."""
        dialog = LoginDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        session = UserSession(dialog.username_key, dialog.display_name, self.vocabulary)
        self.window = MainWindow(session, self.settings)
        self.window.session_ended.connect(self.on_session_ended)
        self.window.show()
        return True

    def on_session_ended(self, reason):
        self.settings = self.window.settings
        if reason == SESSION_END_SWITCH:
            QTimer.singleShot(0, self.restart_login)
        else:
            self.app.quit()

    def restart_login(self):
        if not self.show_login():
            self.app.quit()


def main():
    app = QApplication(sys.argv)
    settings = load_settings()
    apply_theme(app, settings.theme)
    apply_app_font(app, settings.font_size)

    if not VOCA_PATH.exists():
        QMessageBox.critical(
            None, APP_TITLE,
            f"단어 파일을 찾을 수 없습니다.\n{VOCA_PATH}\n\nvoca.csv를 프로그램과 같은 폴더에 두고 다시 실행하세요.",
        )
        return 1

    vocabulary = Vocabulary.load()
    controller = AppController(app, vocabulary, settings)
    if not controller.show_login():
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
