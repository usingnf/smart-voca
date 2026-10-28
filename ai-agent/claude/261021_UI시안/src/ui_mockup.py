#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - PyQt6 UI 시안 (샘플 데이터, 실제 로직 없음)
# 파일 위치: ai-agent/claude/261021_UI시안/src/ui_mockup.py

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

WINDOW_TITLE = "스마트 보카"
KOREAN_FONT_FAMILY = "Malgun Gothic"
FONT_SIZE = 10
THEME_LIGHT = "밝게"
THEME_DARK = "어둡게"
WINDOW_SIZE = (900, 560)
MENU_ITEMS = ["암기", "시험", "과제", "단어 추가", "유사 의미 검색", "보고서", "계정 관리"]
SAMPLE_WORD = ("federation", "연방, 연합")


def build_title(text):
    """화면 상단 제목 라벨을 만든다."""
    label = QLabel(text)
    label.setStyleSheet("font-size: 18px; font-weight: bold;")
    return label


class LoginDialog(QDialog):
    """실행 시 사용자명만 입력받는 계정 선택 창."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("계정 선택")
        self.setFixedSize(320, 150)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("사용자명 (영문·숫자·한글 1~20자)")
        confirm_button = QPushButton("시작")
        confirm_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("사용자명을 입력하세요"))
        layout.addWidget(self.username_input)
        layout.addWidget(confirm_button)


class MemorizePage(QWidget):
    """암기 화면: 영어 또는 한글을 먼저 보고, 클릭하면 대응하는 답이 열린다."""

    def __init__(self):
        super().__init__()
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["영어 → 한글", "한글 → 영어"])
        self.question_label = QLabel(SAMPLE_WORD[0])
        self.question_label.setStyleSheet("font-size: 28px;")
        self.answer_label = QLabel("")
        self.answer_label.setStyleSheet("font-size: 20px; color: #1565c0;")
        open_button = QPushButton("열기")
        open_button.clicked.connect(lambda: self.answer_label.setText(SAMPLE_WORD[1]))
        next_button = QPushButton("다음 단어")

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("암기"))
        layout.addWidget(self.direction_combo)
        layout.addStretch()
        layout.addWidget(self.question_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.answer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addWidget(open_button)
        buttons.addWidget(next_button)
        layout.addLayout(buttons)


class TestPage(QWidget):
    """시험 설정 화면과 결과 화면 (샘플 결과 표 포함)."""

    def __init__(self):
        super().__init__()
        self.count_spin = QSpinBox()
        self.count_spin.setRange(5, 50)
        self.count_spin.setSingleStep(5)
        self.count_spin.setValue(20)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["영어 → 한글", "한글 → 영어", "복합"])
        self.type_checks = [QCheckBox(name) for name in ["단답형", "4지선다", "OX"]]
        for check in self.type_checks:
            check.setChecked(True)
        start_button = QPushButton("시험 시작")

        result_table = QTableWidget(3, 4)
        result_table.setHorizontalHeaderLabels(["단어", "내 답", "정답", "결과"])
        sample_rows = [
            ("federation", "연방", "연방, 연합", "정답"),
            ("druid", "사제", "드루이드", "오답"),
            ("duchy", "공국", "공국, 공작령", "정답"),
        ]
        for row_index, row in enumerate(sample_rows):
            for column_index, value in enumerate(row):
                result_table.setItem(row_index, column_index, QTableWidgetItem(value))

        settings_form = QHBoxLayout()
        settings_form.addWidget(QLabel("문제 수"))
        settings_form.addWidget(self.count_spin)
        settings_form.addWidget(QLabel("방향"))
        settings_form.addWidget(self.direction_combo)
        for check in self.type_checks:
            settings_form.addWidget(check)

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("시험"))
        layout.addLayout(settings_form)
        layout.addWidget(start_button)
        layout.addWidget(QLabel("최종 결과 (샘플): 오답은 정답을 함께 표시"))
        layout.addWidget(result_table)


class AssignmentPage(QWidget):
    """일일 과제 화면: 구성과 완수 기준을 보여 준다."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(build_title("오늘의 과제"))
        layout.addWidget(QLabel("과제 20개 (복습 7 / 신규 13)"))
        layout.addWidget(QLabel("완수 기준: 과제 시험 정답률 80% 이상 (16/20 이상)"))
        layout.addWidget(QLabel("상태: 미완수"))
        layout.addStretch()
        layout.addWidget(QPushButton("과제 시험 시작"))


class AddWordPage(QWidget):
    """단어 추가 화면: 사용자가 영단어와 한글 뜻을 직접 입력한다."""

    def __init__(self):
        super().__init__()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("영단어")
        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText("한글 뜻")

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("단어 추가"))
        layout.addWidget(self.word_input)
        layout.addWidget(self.meaning_input)
        layout.addWidget(QPushButton("추가"))
        layout.addStretch()


class SearchPage(QWidget):
    """유사 의미 검색 화면: 영어 단어 또는 한글 뜻으로 검색한다."""

    def __init__(self):
        super().__init__()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("영어 단어 또는 한글 뜻")
        result_list = QListWidget()
        result_list.addItems(["유의어: alliance, union, league (샘플)"])

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("유사 의미 검색"))
        layout.addWidget(self.query_input)
        layout.addWidget(QPushButton("검색"))
        layout.addWidget(result_list)


class ReportPage(QWidget):
    """보고서 화면: 기간 선택과 오답률 상위 10개 표를 보여 준다."""

    def __init__(self):
        super().__init__()
        period_combo = QComboBox()
        period_combo.addItems(["전체", "최근 7일", "최근 30일", "기간 선택"])
        table = QTableWidget(2, 3)
        table.setHorizontalHeaderLabels(["단어", "출제", "오답률"])
        table.setItem(0, 0, QTableWidgetItem("druid"))
        table.setItem(0, 1, QTableWidgetItem("4"))
        table.setItem(0, 2, QTableWidgetItem("50%"))
        table.setItem(1, 0, QTableWidgetItem("duchy"))
        table.setItem(1, 1, QTableWidgetItem("2"))
        table.setItem(1, 2, QTableWidgetItem("0%"))

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("보고서"))
        layout.addWidget(period_combo)
        layout.addWidget(QLabel("과제 이수율: 샘플 60% / 암기한 단어 수: 샘플 35개"))
        layout.addWidget(QLabel("오답률 상위 단어 (최대 10개)"))
        layout.addWidget(table)
        layout.addWidget(QPushButton("HTML 보고서 열기"))


class AccountPage(QWidget):
    """계정 관리 화면: 삭제와 초기화는 확인 창을 거친다."""

    def __init__(self):
        super().__init__()
        reset_button = QPushButton("기록 초기화")
        reset_button.clicked.connect(lambda: self.confirm_action("기록 초기화", "오답률, 이력, 과제 상태를 지웁니다."))
        delete_button = QPushButton("계정 삭제")
        delete_button.clicked.connect(lambda: self.confirm_action("계정 삭제", "계정과 모든 데이터를 지웁니다."))

        layout = QVBoxLayout(self)
        layout.addWidget(build_title("계정 관리"))
        layout.addWidget(QLabel("현재 사용자: 샘플"))
        layout.addWidget(reset_button)
        layout.addWidget(delete_button)
        layout.addStretch()

    def confirm_action(self, action_name, warning_text):
        """되돌릴 수 없음을 표시한 확인 창을 띄운다 (실제 삭제는 하지 않는다)."""
        answer = QMessageBox.warning(
            self,
            action_name,
            f"{warning_text}\n이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, action_name, "(시안) 실제 작업은 수행하지 않았습니다.")


class MainWindow(QMainWindow):
    """왼쪽 메뉴 + 오른쪽 작업 영역 구조의 메인 창."""

    def __init__(self, username):
        super().__init__()
        self.setWindowTitle(f"{WINDOW_TITLE} - {username}")
        self.setFixedSize(*WINDOW_SIZE)

        self.menu_list = QListWidget()
        self.menu_list.addItems(MENU_ITEMS)
        self.menu_list.setFixedWidth(160)

        self.pages = QStackedWidget()
        for page in [
            MemorizePage(), TestPage(), AssignmentPage(), AddWordPage(),
            SearchPage(), ReportPage(), AccountPage(),
        ]:
            self.pages.addWidget(page)

        self.menu_list.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.menu_list.setCurrentRow(0)

        self.current_theme = THEME_LIGHT
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)
        self.update_theme_button()

        side_column = QVBoxLayout()
        side_column.addWidget(self.menu_list, stretch=1)
        side_column.addWidget(self.theme_button)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addLayout(side_column)
        layout.addWidget(self.pages, stretch=1)
        self.setCentralWidget(central)

    def toggle_theme(self):
        """밝게와 어둡게를 전환한다 (앱 전체 팔레트 변경)."""
        next_theme = THEME_DARK if self.current_theme == THEME_LIGHT else THEME_LIGHT
        self.current_theme = next_theme
        apply_theme(QApplication.instance(), self.current_theme)
        self.update_theme_button()

    def update_theme_button(self):
        """버튼에는 누르면 바뀌는 테마 이름을 표시한다."""
        target_theme = THEME_DARK if self.current_theme == THEME_LIGHT else THEME_LIGHT
        self.theme_button.setText(f"{target_theme}로 보기")


def apply_app_font(app):
    """한글이 깨지지 않도록 앱 전체 글꼴을 맑은 고딕으로 지정한다."""
    app.setFont(QFont(KOREAN_FONT_FAMILY, FONT_SIZE))


def build_dark_palette():
    """어두운 배경과 밝은 글자를 쓰는 팔레트를 만든다."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(66, 135, 245))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return palette


def apply_theme(app, theme_name):
    """Fusion 스타일로 통일한 뒤 밝게/어둡게 팔레트를 적용한다.

    Windows 기본 스타일은 팔레트를 일부만 반영하므로 Fusion을 쓴다.
    """
    app.setStyle("Fusion")
    if theme_name == THEME_DARK:
        app.setPalette(build_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())


def main():
    app = QApplication(sys.argv)
    apply_app_font(app)
    apply_theme(app, THEME_LIGHT)
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0
    username = login.username_input.text().strip()
    window = MainWindow(username)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
