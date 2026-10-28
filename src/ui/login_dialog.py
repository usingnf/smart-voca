#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 사용자명만 입력받는 계정 선택 창
# 파일 위치: src/ui/login_dialog.py

from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from config import APP_TITLE
from user_store import normalize_username


class LoginDialog(QDialog):
    """사용자명을 입력하면 accepted 상태로 닫힌다. 결과는 username_key와 display_name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_TITLE} - 계정 선택")
        self.setMinimumWidth(340)
        self.username_key = None
        self.display_name = None

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("사용자명 (영문·숫자·한글 1~20자)")
        self.username_input.returnPressed.connect(self.try_accept)

        start_button = QPushButton("시작")
        start_button.clicked.connect(self.try_accept)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("사용자명을 입력하세요. 처음 입력하면 계정이 만들어집니다."))
        layout.addWidget(self.username_input)
        layout.addWidget(start_button)

    def try_accept(self):
        key = normalize_username(self.username_input.text())
        if key is None:
            QMessageBox.warning(self, "사용자명 오류",
                                "사용자명은 영문·숫자·한글 1~20자로 입력하세요.")
            return
        self.username_key = key
        self.display_name = self.username_input.text().strip()
        self.accept()
