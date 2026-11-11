#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 메인 창 (왼쪽 메뉴, 계정 전환, 테마·옵션 적용, 화면 전환)
# 파일 위치: src/ui/main_window.py

from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import APP_TITLE
from settings import THEME_DARK, THEME_LIGHT, save_settings
from ui.options_page import OptionsPage
from ui.report_pages import AccountPage, ReportPage
from ui.study_pages import AddWordPage, MemorizePage, SearchPage
from ui.test_pages import AssignmentPage, TestPage
from ui.theme import apply_app_font, apply_font_levels, apply_theme

# 메뉴 구성: (표시 이름, 화면 번호). 화면 번호가 None이면 묶음 제목이다.
# 화면 번호는 self.pages에 넣는 순서와 같다.
MENU_LAYOUT = [
    ("학습", None),
    ("▣  암기", 0),
    ("✎  시험", 1),
    ("☑  과제", 2),
    ("⌕  유사 의미 검색", 4),
    ("관리", None),
    ("＋  단어 추가", 3),
    ("▤  보고서", 5),
    ("⚙  옵션", 6),
    ("◉  계정 관리", 7),
]
SESSION_END_QUIT = "quit"
SESSION_END_SWITCH = "switch"


class MainWindow(QMainWindow):
    """왼쪽 메뉴와 오른쪽 작업 영역으로 구성된 메인 창.

    창이 닫힐 때 session_ended로 이유를 알린다. quit은 프로그램 종료, switch는 계정 선택 창으로 돌아간다.
    """

    session_ended = pyqtSignal(str)

    def __init__(self, session, settings):
        super().__init__()
        self.session = session
        self.settings = settings
        self.session_end_reason = SESSION_END_QUIT
        self.setWindowTitle(f"{APP_TITLE} - {session.display_name}")
        self.resize(settings.window_width, settings.window_height)

        self.menu_list = QListWidget()
        self.menu_list.setMinimumWidth(170)
        self.menu_list.setAlternatingRowColors(False)
        self._build_menu()

        self.memorize_page = MemorizePage(session)
        self.test_page = TestPage(session)
        self.assignment_page = AssignmentPage(session)
        self.search_page = SearchPage(session)
        self.report_page = ReportPage(session)
        self.options_page = OptionsPage(settings)
        self.options_page.settings_changed.connect(self.apply_settings)
        self.account_page = AccountPage(session)
        self.account_page.reset_done.connect(self.refresh_pages)
        self.account_page.account_deleted.connect(self.request_switch)
        self.test_page.preferences_changed.connect(self.save_test_preferences)

        self.pages = QStackedWidget()
        for page in [
            self.memorize_page, self.test_page, self.assignment_page,
            AddWordPage(session), self.search_page, self.report_page,
            self.options_page, self.account_page,
        ]:
            self.pages.addWidget(page)

        self.menu_list.currentRowChanged.connect(self.on_menu_changed)
        self.menu_list.setCurrentRow(self._first_selectable_row())

        self.switch_button = QPushButton("계정 전환")
        self.switch_button.clicked.connect(self.request_switch)
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)

        side_column = QVBoxLayout()
        side_column.addWidget(self.menu_list, stretch=1)
        side_column.addWidget(self.switch_button)
        side_column.addWidget(self.theme_button)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addLayout(side_column)
        layout.addWidget(self.pages, stretch=1)
        self.setCentralWidget(central)

        self.apply_settings(settings, save=False)
        self.show_pending_notice()

    def apply_settings(self, new_settings, save=True):
        """옵션을 적용한다. 저장을 원하면 settings.json에도 쓴다."""
        self.settings = new_settings.sanitized()
        app = QApplication.instance()
        apply_theme(app, self.settings.theme)
        apply_app_font(app, self.settings.font_size)
        apply_font_levels(app, self)
        self.memorize_page.apply_settings(self.settings)
        self.test_page.apply_settings(self.settings)
        self.search_page.set_online_settings(self.settings.online_lookup_enabled, self.settings.krdict_api_key)
        self.options_page.load_values(self.settings)
        self.update_theme_button()
        if save:
            save_settings(self.settings)

    def update_theme_button(self):
        target = THEME_DARK if self.settings.theme == THEME_LIGHT else THEME_LIGHT
        self.theme_button.setText(f"{target}로 보기")

    def toggle_theme(self):
        target = THEME_DARK if self.settings.theme == THEME_LIGHT else THEME_LIGHT
        self.apply_settings(replace(self.settings, theme=target))

    def _build_menu(self):
        """묶음 제목은 고를 수 없는 굵은 줄로, 화면 항목은 화면 번호를 달고 넣는다."""
        for label, page_index in MENU_LAYOUT:
            item = QListWidgetItem(label)
            if page_index is None:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                font = QFont(item.font())
                font.setBold(True)
                item.setFont(font)
            else:
                item.setData(Qt.ItemDataRole.UserRole, page_index)
            self.menu_list.addItem(item)

    def _first_selectable_row(self):
        for row in range(self.menu_list.count()):
            if self.menu_list.item(row).data(Qt.ItemDataRole.UserRole) is not None:
                return row
        return 0

    def save_test_preferences(self, preferences):
        """시험 화면에서 고른 조건을 설정에 반영하고 저장한다. 화면 칸은 다시 채우지 않는다 (입력 중 깜빡임 방지)."""
        self.settings = replace(self.settings, **preferences)
        save_settings(self.settings)

    def on_menu_changed(self, row):
        item = self.menu_list.item(row)
        page_index = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if page_index is None:
            return
        self.pages.setCurrentIndex(page_index)
        page = self.pages.currentWidget()
        if page is self.assignment_page:
            self.assignment_page.refresh()
        elif page is self.report_page:
            self.report_page.refresh()

    def refresh_pages(self):
        self.assignment_page.refresh()
        self.report_page.refresh()

    def request_switch(self):
        """계정 선택 창으로 돌아간다."""
        self.session_end_reason = SESSION_END_SWITCH
        self.close()

    def show_pending_notice(self):
        """오늘 과제가 아직 남아 있으면 상태 표시줄에 알린다. 과제가 없으면 새로 만든다."""
        self.session.today_assignment()
        if self.session.pending_today():
            self.statusBar().showMessage("오늘 과제가 아직 남아 있습니다. [과제] 메뉴에서 시험을 보세요.")

    def closeEvent(self, event):
        self.search_page.shutdown()
        size = self.size()
        if (size.width(), size.height()) != (self.settings.window_width, self.settings.window_height):
            self.apply_settings(replace(self.settings, window_width=size.width(),
                                        window_height=size.height()))
        self.session_ended.emit(self.session_end_reason)
        super().closeEvent(event)
