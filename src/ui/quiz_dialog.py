#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 시험 진행 창과 결과 창 (진행률, 키보드 조작, 정답·오답 표시, 오답만 보기)
# 파일 위치: src/ui/quiz_dialog.py

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz import KIND_OX, KIND_SHORT, OX_FALSE, OX_TRUE, grade_answers, score_of
from ui.theme import mark_font_level, result_colors

MARK_CORRECT = "✓ 정답"
MARK_WRONG = "✗ 오답"
OX_KEYS = {Qt.Key.Key_O: OX_TRUE, Qt.Key.Key_X: OX_FALSE}
NUMBER_KEYS = [Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4]


class QuizDialog(QDialog):
    """문항을 하나씩 풀고, 끝나면 결과 화면을 보여 준다.

    키보드: 4지선다는 1~4, OX는 O/X, 단답은 Enter로 제출한다.
    중도 종료하면 aborted가 True가 된다. 결과는 기록하지 않는다.
    pass_rate가 주어지면 결과 화면에 통과 여부를 표시한다 (과제 시험용).
    """

    def __init__(self, questions, title, pass_rate=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(780, 520)
        self.questions = questions
        self.pass_rate = pass_rate
        self.answers = []
        self.results = []
        self.finished = False
        self.aborted = False
        self.current_choices = []

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(questions))
        self.progress_bar.setTextVisible(False)
        self.progress_label = QLabel()
        self.prompt_label = QLabel()
        self.prompt_label.setWordWrap(True)
        mark_font_level(self.prompt_label, "large")
        self.hint_label = QLabel()
        self.answer_area = QWidget()
        self.answer_layout = QVBoxLayout(self.answer_area)

        question_page = QWidget()
        question_layout = QVBoxLayout(question_page)
        question_layout.addWidget(self.progress_label)
        question_layout.addWidget(self.progress_bar)
        question_layout.addStretch()
        question_layout.addWidget(self.prompt_label)
        question_layout.addStretch()
        question_layout.addWidget(self.answer_area)
        question_layout.addWidget(self.hint_label)

        self.summary_label = QLabel()
        self.wrong_only_check = QCheckBox("오답만 보기")
        self.wrong_only_check.toggled.connect(self._apply_wrong_filter)
        self.result_table = QTableWidget(0, 6)
        self.result_table.setHorizontalHeaderLabels(["단어", "방향", "유형", "내 답", "정답", "결과"])
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        result_page = QWidget()
        result_layout = QVBoxLayout(result_page)
        result_layout.addWidget(self.summary_label)
        result_layout.addWidget(self.wrong_only_check)
        result_layout.addWidget(self.result_table)
        result_layout.addWidget(close_button)

        self.pages = QStackedWidget()
        self.pages.addWidget(question_page)
        self.pages.addWidget(result_page)
        outer = QVBoxLayout(self)
        outer.addWidget(self.pages)

        self.show_question()

    def show_question(self):
        question = self.questions[len(self.answers)]
        self.progress_bar.setValue(len(self.answers))
        self.progress_label.setText(f"{len(self.answers) + 1} / {len(self.questions)}   ({question.kind})")
        self.prompt_label.setText(question.prompt)
        self._clear_answer_area()
        self.current_choices = []

        if question.kind == KIND_SHORT:
            answer_input = QLineEdit()
            answer_input.setPlaceholderText("정답을 입력하세요 (대소문자·띄어쓰기는 무시)")
            answer_input.returnPressed.connect(lambda: self.submit(answer_input.text()))
            submit_button = QPushButton("확인")
            submit_button.clicked.connect(lambda: self.submit(answer_input.text()))
            row = QHBoxLayout()
            row.addWidget(answer_input)
            row.addWidget(submit_button)
            self.answer_layout.addLayout(row)
            answer_input.setFocus()
            self.hint_label.setText("Enter 키로 제출합니다.")
        else:
            self.current_choices = list(question.choices)
            for index, choice in enumerate(question.choices):
                label = f"{index + 1}. {choice}" if question.kind != KIND_OX else choice
                button = QPushButton(label)
                button.clicked.connect(lambda _checked, text=choice: self.submit(text))
                self.answer_layout.addWidget(button)
            hint = "키 1~4로 고릅니다." if question.kind != KIND_OX else "키 O / X로 고릅니다."
            self.hint_label.setText(hint)

    def keyPressEvent(self, event: QKeyEvent):
        """보기 번호나 O/X 키로 답을 고른다. 결과 화면에서는 무시한다."""
        if self.finished or not self.current_choices:
            super().keyPressEvent(event)
            return
        question = self.questions[len(self.answers)]
        key = event.key()
        if question.kind == KIND_OX:
            if key in OX_KEYS:
                self.submit(OX_KEYS[key])
                return
        elif key in NUMBER_KEYS:
            index = NUMBER_KEYS.index(key)
            if index < len(self.current_choices):
                self.submit(self.current_choices[index])
                return
        super().keyPressEvent(event)

    def submit(self, answer):
        self.answers.append(answer)
        if len(self.answers) < len(self.questions):
            self.show_question()
            return
        self.finish_quiz()

    def finish_quiz(self):
        self.finished = True
        self.progress_bar.setValue(len(self.questions))
        self.results = grade_answers(self.questions, self.answers)
        self._fill_result_table()
        score = score_of(self.results)
        correct = sum(1 for result in self.results if result.is_correct)
        text = f"정답률 {score * 100:.0f}% ({correct} / {len(self.results)})"
        if self.pass_rate is not None:
            verdict = "통과" if score >= self.pass_rate else "미통과"
            text += f"   기준 {self.pass_rate * 100:.0f}% → {verdict}"
        self.summary_label.setText(text)
        correct_color, wrong_color = result_colors(QApplication.palette())
        passed = self.pass_rate is None or score >= self.pass_rate
        summary_color = correct_color if passed else wrong_color
        self.summary_label.setStyleSheet(f"color: {summary_color.name()}; font-weight: bold;")
        self.pages.setCurrentIndex(1)

    def reject(self):
        """ESC나 창 닫기. 결과 화면이면 바로 닫고, 푸는 중이면 중도 종료를 확인한다."""
        if self.finished:
            self.accept()
            return
        answer = QMessageBox.question(
            self, "중도 종료",
            "시험을 끝까지 치르지 않고 나가면 결과가 기록되지 않습니다. 종료할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.aborted = True
            super().reject()

    def _fill_result_table(self):
        correct_color, wrong_color = result_colors(QApplication.palette())
        self.result_table.setRowCount(len(self.results))
        for row_index, result in enumerate(self.results):
            color = QBrush(correct_color if result.is_correct else wrong_color)
            verdict = MARK_CORRECT if result.is_correct else MARK_WRONG
            values = [result.word, result.direction, result.kind, result.user_answer,
                      result.expected_text, verdict]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setForeground(color)
                if column_index == 5:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.result_table.setItem(row_index, column_index, item)
        self._apply_wrong_filter(self.wrong_only_check.isChecked())

    def _apply_wrong_filter(self, wrong_only):
        for row_index, result in enumerate(self.results):
            self.result_table.setRowHidden(row_index, wrong_only and result.is_correct)

    def _clear_answer_area(self):
        _clear_layout(self.answer_layout)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())
