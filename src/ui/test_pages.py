#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 시험 설정(오답 재시험·즐겨찾기 포함) 화면과 오늘의 과제 화면
# 파일 위치: src/ui/test_pages.py

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import (
    DAILY_ASSIGNMENT_SIZE,
    EXAM_QUESTION_DEFAULT,
    EXAM_QUESTION_MAX,
    EXAM_QUESTION_MIN,
    EXAM_QUESTION_STEP,
    PASS_RATE,
    POS_DEFAULT_ORDER,
    RECORD_ASSIGNMENT_TEST,
    RECORD_TEST,
    STATUS_COMPLETED,
    STATUS_MISSED,
    STATUS_PENDING,
)
from quiz import (
    DIRECTION_EN_TO_KO,
    DIRECTION_KO_TO_EN,
    DIRECTION_MIXED,
    KIND_CHOICE,
    KIND_OX,
    KIND_SHORT,
    build_questions,
)
from ui.quiz_dialog import QuizDialog
from ui.study_pages import make_table, page_title
from vocab import POS_LABELS, filter_by_pos, join_list

DIRECTION_CHOICES = [DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN, DIRECTION_MIXED]
TYPE_CHOICES = [(KIND_SHORT, "단답형"), (KIND_CHOICE, "4지선다형"), (KIND_OX, "OX형")]
STATUS_LABELS = {
    STATUS_PENDING: "진행 중 (시험 전)",
    STATUS_COMPLETED: "✓ 완수",
    STATUS_MISSED: "✗ 미이수",
}
MAX_RETEST_WORDS = EXAM_QUESTION_MAX
MAX_CHIP_WIDTH = 4


def make_chip(text, color):
    """배경색이 있는 작은 표시 칸 (복습·신규 구분용)."""
    chip = QLabel(text)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setStyleSheet(
        f"background-color: {color}; color: white; border-radius: 6px; padding: 4px 10px; font-weight: bold;"
    )
    return chip


class TestPage(QWidget):
    """시험 설정 화면. 문제 수, 방향, 유형, 품사를 고른 뒤 시작한다.

    오답 재시험과 즐겨찾기만 출제도 여기서 한다.
    """

    def __init__(self, session):
        super().__init__()
        self.session = session

        self.count_spin = QSpinBox()
        self.count_spin.setRange(EXAM_QUESTION_MIN, EXAM_QUESTION_MAX)
        self.count_spin.setSingleStep(EXAM_QUESTION_STEP)
        self.count_spin.setValue(EXAM_QUESTION_DEFAULT)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(DIRECTION_CHOICES)
        self.type_checks = []
        for kind, label in TYPE_CHOICES:
            check = QCheckBox(label)
            check.setChecked(True)
            check.setProperty("kind", kind)
            self.type_checks.append(check)
        self.pos_checks = []
        for pos_key in POS_DEFAULT_ORDER:
            check = QCheckBox(POS_LABELS[pos_key])
            check.setChecked(True)
            check.setProperty("posKey", pos_key)
            self.pos_checks.append(check)
        self.favorites_check = QCheckBox("즐겨찾기 단어만 출제")
        start_button = QPushButton("시험 시작")
        start_button.clicked.connect(self.start_test)
        retest_button = QPushButton("오답 재시험")
        retest_button.clicked.connect(self.start_wrong_retest)
        self.retest_hint = QLabel()

        settings = QHBoxLayout()
        settings.addWidget(QLabel("문제 수"))
        settings.addWidget(self.count_spin)
        settings.addWidget(QLabel("방향"))
        settings.addWidget(self.direction_combo)
        for check in self.type_checks:
            settings.addWidget(check)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("출제 품사"))
        for check in self.pos_checks:
            pos_row.addWidget(check)
        pos_row.addStretch()

        buttons = QHBoxLayout()
        buttons.addWidget(start_button)
        buttons.addWidget(retest_button)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("시험"))
        layout.addLayout(settings)
        layout.addLayout(pos_row)
        layout.addWidget(self.favorites_check)
        layout.addLayout(buttons)
        layout.addWidget(self.retest_hint)
        layout.addStretch()

        self.refresh_hint()

    def apply_settings(self, settings):
        self.count_spin.setValue(settings.exam_count)
        self.direction_combo.setCurrentText(settings.exam_direction)

    def refresh_hint(self):
        wrong_count = len(self.session.wrong_words())
        self.retest_hint.setText(f"최근 시험에서 틀린 단어: {wrong_count}개")

    def selected_kinds(self):
        return [check.property("kind") for check in self.type_checks if check.isChecked()]

    def selected_pos_keys(self):
        return [check.property("posKey") for check in self.pos_checks if check.isChecked()]

    def _run_quiz(self, targets, title):
        """문항을 만들어 시험 창을 띄우고, 끝나면 기록한다."""
        kinds = self.selected_kinds()
        if not kinds:
            QMessageBox.warning(self, "유형 선택", "문제 유형을 하나 이상 선택하세요.")
            return
        pool = self.session.pool
        questions = build_questions(targets, pool, self.direction_combo.currentText(),
                                    kinds, self.session.rng)
        dialog = QuizDialog(questions, title, parent=self)
        dialog.exec()
        if dialog.finished:
            self.session.record_results(dialog.results, RECORD_TEST)
        self.refresh_hint()

    def start_test(self):
        if not self.selected_kinds():
            QMessageBox.warning(self, "유형 선택", "문제 유형을 하나 이상 선택하세요.")
            return
        pos_keys = self.selected_pos_keys()
        if not pos_keys:
            QMessageBox.warning(self, "품사 선택", "출제할 품사를 하나 이상 선택하세요.")
            return
        # 보기(오답 후보)는 전체 풀에서 고르고, 정답 단어만 선택한 조건으로 제한한다.
        pool = self.session.pool
        candidates = filter_by_pos(pool, pos_keys)
        if self.favorites_check.isChecked():
            candidates = {word: entry for word, entry in candidates.items()
                          if self.session.is_favorite(word)}
        candidate_list = list(candidates.values())
        if not candidate_list:
            QMessageBox.warning(self, "단어 없음", "조건에 맞는 단어가 없습니다. 품사나 즐겨찾기 조건을 확인하세요.")
            return
        requested = self.count_spin.value()
        count = min(requested, len(candidate_list))
        if count < requested:
            QMessageBox.information(
                self, "문제 수 조정",
                f"조건에 맞는 단어가 {len(candidate_list)}개뿐이라 {count}문항으로 출제합니다.",
            )
        targets = self.session.rng.sample(candidate_list, count)
        self._run_quiz(targets, "시험")

    def start_wrong_retest(self):
        words = [word for word in self.session.wrong_words() if word in self.session.pool]
        if not words:
            QMessageBox.information(self, "오답 재시험", "최근 시험에서 틀린 단어가 없습니다.")
            return
        words = words[:MAX_RETEST_WORDS]
        targets = [self.session.pool[word] for word in words]
        self._run_quiz(targets, "오답 재시험")


class AssignmentPage(QWidget):
    """오늘의 과제 화면. 구성과 상태를 색 칩과 표로 보여 주고, 과제 시험을 시작한다."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.assignment = None

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: bold;")
        self.chip_row = QHBoxLayout()
        self.word_table = make_table(["단어", "한글 뜻", "구분"])
        self.start_button = QPushButton("과제 시험 시작")
        self.start_button.clicked.connect(self.start_assignment_test)
        self.rule_label = QLabel(
            f"완수 기준: 과제 시험 정답률 {PASS_RATE * 100:.0f}% 이상 "
            f"({DAILY_ASSIGNMENT_SIZE}문항 중 {int(DAILY_ASSIGNMENT_SIZE * PASS_RATE)}개 이상 정답)"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("오늘의 과제"))
        layout.addWidget(self.status_label)
        layout.addLayout(self.chip_row)
        layout.addWidget(self.rule_label)
        layout.addWidget(self.word_table)
        layout.addWidget(self.start_button)

        self.refresh()

    def refresh(self):
        self.assignment = self.session.today_assignment()
        assignment = self.assignment
        status = STATUS_LABELS.get(assignment["status"], assignment["status"])
        score_text = "" if assignment["score"] is None else f"   최근 점수 {assignment['score'] * 100:.0f}%"
        self.status_label.setText(f"{assignment['date']}   상태: {status}{score_text}")

        self._clear_chips()
        self.chip_row.addWidget(make_chip(f"복습 {len(assignment['review'])}", "#ef6c00"))
        self.chip_row.addWidget(make_chip(f"신규 {len(assignment['new'])}", "#1565c0"))
        self.chip_row.addWidget(make_chip(f"합계 {len(assignment['words'])}", "#546e7a"))
        self.chip_row.addStretch()

        review_words = set(assignment["review"])
        self.word_table.setRowCount(len(assignment["words"]))
        for row_index, word in enumerate(assignment["words"]):
            entry = self.session.pool.get(word)
            meaning = join_list(entry.meanings) if entry else ""
            kind = "복습" if word in review_words else "신규"
            self.word_table.setItem(row_index, 0, QTableWidgetItem(word))
            self.word_table.setItem(row_index, 1, QTableWidgetItem(meaning))
            self.word_table.setItem(row_index, 2, QTableWidgetItem(kind))
        self.start_button.setEnabled(assignment["status"] == STATUS_PENDING)

    def _clear_chips(self):
        while self.chip_row.count():
            item = self.chip_row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def start_assignment_test(self):
        assignment = self.assignment
        pool = self.session.pool
        targets = [pool[word] for word in assignment["words"] if word in pool]
        kinds = [KIND_SHORT, KIND_CHOICE, KIND_OX]
        questions = build_questions(targets, pool, DIRECTION_MIXED, kinds, self.session.rng)

        dialog = QuizDialog(questions, "과제 시험", pass_rate=PASS_RATE, parent=self)
        dialog.exec()
        if dialog.aborted:
            self.session.abandon_assignment(assignment)
        elif dialog.finished:
            self.session.record_results(dialog.results, RECORD_ASSIGNMENT_TEST)
            self.session.finish_assignment(assignment, dialog.results)
        self.refresh()

