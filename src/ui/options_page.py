#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 옵션 화면 (테마, 글꼴 크기, 시험·암기 기본값). 바꾸면 바로 저장·적용
# 파일 위치: src/ui/options_page.py

import re
from dataclasses import replace

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import EXAM_QUESTION_MAX, EXAM_QUESTION_MIN, EXAM_QUESTION_STEP
from settings import (
    DIRECTION_CHOICES,
    FONT_SIZE_MAX,
    FONT_SIZE_MIN,
    THEME_CHOICES,
    AppSettings,
)
from ui.study_pages import page_title

KRDICT_KEY_PATTERN = re.compile(r"^[0-9A-Fa-f]{32}$")


class OptionsPage(QWidget):
    """옵션 화면. 값을 바꾸면 settings_changed로 알리고, 메인 창이 저장·적용한다."""

    settings_changed = pyqtSignal(object)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._loading = False

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_CHOICES)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(FONT_SIZE_MIN, FONT_SIZE_MAX)
        self.font_spin.setSuffix(" pt")
        self.exam_count_spin = QSpinBox()
        self.exam_count_spin.setRange(EXAM_QUESTION_MIN, EXAM_QUESTION_MAX)
        self.exam_count_spin.setSingleStep(EXAM_QUESTION_STEP)
        self.exam_direction_combo = QComboBox()
        self.exam_direction_combo.addItems(DIRECTION_CHOICES)
        self.memorize_direction_combo = QComboBox()
        self.memorize_direction_combo.addItems(DIRECTION_CHOICES[:2])
        self.online_check = QCheckBox("온라인 한→영 보조 검색 사용 (유사 의미 검색 화면)")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("한국어기초사전 인증키 (32자리)")
        self.key_show_check = QCheckBox("보기")
        self.key_show_check.toggled.connect(self.toggle_key_visibility)
        self.key_save_button = QPushButton("저장")
        self.key_save_button.clicked.connect(self.save_key)
        self.key_status_label = QLabel()
        self.key_status_label.setWordWrap(True)
        self._saved_key = ""
        reset_button = QPushButton("기본값으로 되돌리기")
        reset_button.clicked.connect(self.restore_defaults)

        for combo in [self.theme_combo, self.exam_direction_combo, self.memorize_direction_combo]:
            combo.currentIndexChanged.connect(self.on_value_changed)
        for spin in [self.font_spin, self.exam_count_spin]:
            spin.valueChanged.connect(self.on_value_changed)
        self.online_check.toggled.connect(self.on_value_changed)

        title = page_title("옵션")
        note = QLabel("바꾸면 바로 저장되고 적용됩니다. 옵션 파일은 프로그램 폴더의 settings.json입니다.")
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addLayout(self._row("테마", self.theme_combo))
        layout.addLayout(self._row("글꼴 크기", self.font_spin))
        layout.addLayout(self._row("시험 기본 문제 수", self.exam_count_spin))
        layout.addLayout(self._row("시험 기본 방향", self.exam_direction_combo))
        layout.addLayout(self._row("암기 기본 방향", self.memorize_direction_combo))
        layout.addWidget(self.online_check)
        key_box = QWidget()
        key_row = QHBoxLayout(key_box)
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.addWidget(self.key_input, stretch=1)
        key_row.addWidget(self.key_show_check)
        key_row.addWidget(self.key_save_button)
        layout.addLayout(self._row("온라인 인증키", key_box))
        layout.addWidget(self.key_status_label)
        layout.addStretch()
        layout.addWidget(reset_button)

        self.load_values(settings)

    def _row(self, label_text, widget):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(140)
        row.addWidget(label)
        row.addWidget(widget, stretch=1)
        return row

    def load_values(self, settings):
        """현재 설정 값을 입력 칸에 채운다. 채우는 동안에는 신호를 보내지 않는다."""
        self._loading = True
        self.settings = settings
        self.theme_combo.setCurrentText(settings.theme)
        self.font_spin.setValue(settings.font_size)
        self.exam_count_spin.setValue(settings.exam_count)
        self.exam_direction_combo.setCurrentText(settings.exam_direction)
        self.memorize_direction_combo.setCurrentText(settings.memorize_direction)
        self.online_check.setChecked(settings.online_lookup_enabled)
        if settings.krdict_api_key != self._saved_key:
            self._saved_key = settings.krdict_api_key
            self.key_input.setText(settings.krdict_api_key)
            self.key_status_label.setText("")
        self._loading = False

    def toggle_key_visibility(self, show):
        """보기 체크 시 키 원문을 보여 준다. 기본은 가려서 보여 준다."""
        mode = QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        self.key_input.setEchoMode(mode)

    def save_key(self):
        """입력한 키를 검증한 뒤 저장한다. 칸을 비우면 키를 지운다."""
        key = self.key_input.text().strip()
        if key and not KRDICT_KEY_PATTERN.fullmatch(key):
            self.key_status_label.setText("인증키는 영문·숫자 32자리여야 합니다. 다시 확인해 주세요.")
            return
        self.settings = replace(self.settings, krdict_api_key=key).sanitized()
        self.settings_changed.emit(self.settings)
        self.key_status_label.setText("인증키를 지웠습니다." if not key else "인증키를 저장했습니다.")

    def current_values(self):
        """입력 칸의 값을 반영한다. 칸에 없는 값(인증키, 창 크기)은 현재 설정을 그대로 둔다."""
        return replace(
            self.settings,
            theme=self.theme_combo.currentText(),
            font_size=self.font_spin.value(),
            exam_count=self.exam_count_spin.value(),
            exam_direction=self.exam_direction_combo.currentText(),
            memorize_direction=self.memorize_direction_combo.currentText(),
            online_lookup_enabled=self.online_check.isChecked(),
        ).sanitized()

    def on_value_changed(self, *_args):
        if self._loading:
            return
        self.settings = self.current_values()
        self.settings_changed.emit(self.settings)

    def restore_defaults(self):
        """옵션 값만 기본값으로 되돌린다. 인증키와 창 크기는 유지한다."""
        defaults = replace(AppSettings(), krdict_api_key=self.settings.krdict_api_key,
                           window_width=self.settings.window_width,
                           window_height=self.settings.window_height)
        self.load_values(defaults)
        self.settings_changed.emit(self.settings)
