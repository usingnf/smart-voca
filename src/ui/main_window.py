#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 메인 창 (왼쪽 메뉴, 계정 전환, 테마·옵션 적용, 화면 전환)
# 파일 위치: src/ui/main_window.py

from dataclasses import replace

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
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

MENU_ITEMS = ["암기", "시험", "과제", "단어 추가", "유사 의미 검색", "보고서", "옵션", "계정 관리"]
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
        self.menu_list.addItems(MENU_ITEMS)
        self.menu_list.setMinimumWidth(150)
        self.menu_list.setAlternatingRowColors(True)

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

        self.pages = QStackedWidget()
        for page in [
            self.memorize_page, self.test_page, self.assignment_page,
            AddWordPage(session), self.search_page, self.report_page,
            self.options_page, self.account_page,
        ]:
            self.pages.addWidget(page)

        self.menu_list.currentRowChanged.connect(self.on_menu_changed)
        self.menu_list.setCurrentRow(0)

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

    def on_menu_changed(self, index):
        self.pages.setCurrentIndex(index)
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
        size = self.size()
        if (size.width(), size.height()) != (self.settings.window_width, self.settings.window_height):
            self.apply_settings(replace(self.settings, window_width=size.width(),
                                        window_height=size.height()))
        self.session_ended.emit(self.session_end_reason)
        super().closeEvent(event)
