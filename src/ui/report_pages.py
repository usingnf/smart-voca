#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 보고서(그래프·기록 내보내기 포함)와 계정 관리 화면
# 파일 위치: src/ui/report_pages.py

import webbrowser
from pathlib import Path

from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import REPORTS_DIR
from report import (
    PERIOD_CUSTOM,
    PERIOD_OPTIONS,
    build_summary,
    daily_accuracy,
    format_percent,
    period_range,
    write_report,
)
from timeutil import kst_today
from ui.chart import BarChart
from ui.study_pages import make_table, page_title

EMPTY_REPORT_TEXT = "아직 기록이 없습니다. 시험을 보면 이 화면에 결과가 표시됩니다."
CHART_DAYS = 14


class ReportPage(QWidget):
    """보고서 화면. 기간을 고르면 수치, 날짜별 정답률 그래프, 오답률 상위 표를 갱신한다."""

    def __init__(self, session):
        super().__init__()
        self.session = session

        self.period_combo = QComboBox()
        self.period_combo.addItems(PERIOD_OPTIONS)
        self.period_combo.currentIndexChanged.connect(self.refresh)
        today = QDate(kst_today().year, kst_today().month, kst_today().day)
        self.start_edit = self._date_edit(today.addDays(-6))
        self.end_edit = self._date_edit(today)
        self.summary_label = QLabel()
        self.chart = BarChart()
        self.chart_title = QLabel(f"최근 {CHART_DAYS}일 날짜별 시험 정답률")
        self.top_table = make_table(["단어", "출제", "오답", "오답률"])
        self.empty_label = QLabel(EMPTY_REPORT_TEXT)
        self.empty_label.setWordWrap(True)
        export_html_button = QPushButton("HTML 보고서 만들기")
        export_html_button.clicked.connect(self.export_report)
        export_csv_button = QPushButton("기록 CSV 내보내기")
        export_csv_button.clicked.connect(self.export_history_csv)
        self.message_label = QLabel()

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("기간"))
        period_row.addWidget(self.period_combo)
        period_row.addWidget(QLabel("시작"))
        period_row.addWidget(self.start_edit)
        period_row.addWidget(QLabel("끝"))
        period_row.addWidget(self.end_edit)
        button_row = QHBoxLayout()
        button_row.addWidget(export_html_button)
        button_row.addWidget(export_csv_button)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("보고서"))
        layout.addLayout(period_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.chart_title)
        layout.addWidget(self.chart)
        layout.addWidget(QLabel("오답률 상위 단어 (최대 10개, 출제 1회 이상)"))
        layout.addWidget(self.top_table)
        layout.addWidget(self.empty_label)
        layout.addLayout(button_row)
        layout.addWidget(self.message_label)

        self.refresh()

    def _date_edit(self, value):
        edit = QDateEdit(value)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setCalendarPopup(True)
        edit.dateChanged.connect(self.refresh)
        return edit

    def selected_range(self):
        period = self.period_combo.currentText()
        custom = period == PERIOD_CUSTOM
        self.start_edit.setEnabled(custom)
        self.end_edit.setEnabled(custom)
        start = self.start_edit.date().toPyDate()
        end = self.end_edit.date().toPyDate()
        if custom and start > end:
            start, end = end, start
        return period, period_range(period, kst_today(), start, end)

    def refresh(self):
        period, (start, end) = self.selected_range()
        rows = self.session.history()
        summary = build_summary(rows, self.session.state["assignments"], start, end)
        test_rate = summary["test_correct"] / summary["test_total"] if summary["test_total"] else None
        self.summary_label.setText(
            f"과제 이수율: {format_percent(summary['completion_rate'])}   "
            f"암기한 단어 수: {summary['memorized']}개   "
            f"시험 정답률: {format_percent(test_rate)}"
        )
        series = daily_accuracy(rows, kst_today(), CHART_DAYS)
        self.chart.set_items(series)

        self.top_table.setRowCount(len(summary["top_wrong"]))
        for row_index, (word, asked, wrong, rate) in enumerate(summary["top_wrong"]):
            values = [word, str(asked), str(wrong), format_percent(rate)]
            for column_index, value in enumerate(values):
                self.top_table.setItem(row_index, column_index, QTableWidgetItem(value))

        has_records = bool(rows)
        self.empty_label.setVisible(not has_records)
        self.message_label.setText("")

    def export_report(self):
        period, (start, end) = self.selected_range()
        summary = build_summary(self.session.history(),
                                self.session.state["assignments"], start, end)
        path = write_report(self.session.username_key, self.session.display_name, period, summary)
        webbrowser.open(path.as_uri())
        self.message_label.setText(f"저장: {path}")

    def export_history_csv(self):
        """이력 CSV를 사용자가 고른 위치에 복사한다. 기본 위치는 reports 폴더다."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        default_path = REPORTS_DIR / f"{self.session.username_key}_history_{kst_today().isoformat()}.csv"
        target, _ = QFileDialog.getSaveFileName(self, "기록 CSV 저장", str(default_path), "CSV 파일 (*.csv)")
        if not target:
            return
        if self.session.export_history(Path(target)):
            self.message_label.setText(f"저장: {target}")
        else:
            QMessageBox.information(self, "기록 없음", "저장할 기록이 없습니다.")


class AccountPage(QWidget):
    """계정 관리 화면. 초기화와 삭제는 되돌릴 수 없음을 알리고 확인을 받는다."""

    reset_done = pyqtSignal()
    account_deleted = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self.session = session

        reset_button = QPushButton("기록 초기화")
        reset_button.clicked.connect(self.confirm_reset)
        delete_button = QPushButton("계정 삭제")
        delete_button.clicked.connect(self.confirm_delete)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("계정 관리"))
        layout.addWidget(QLabel(f"현재 사용자: {self.session.display_name}"))
        layout.addWidget(QLabel("초기화: 오답률, 이력, 과제 상태를 지웁니다. 계정과 추가한 단어, 즐겨찾기는 남깁니다."))
        layout.addWidget(reset_button)
        layout.addWidget(QLabel("삭제: 계정의 모든 데이터를 지웁니다. 계정이 사라집니다."))
        layout.addWidget(delete_button)
        layout.addStretch()

    def _confirm(self, title, detail):
        answer = QMessageBox.warning(
            self, title,
            f"{detail}\n이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def confirm_reset(self):
        if self._confirm("기록 초기화", "오답률, 이력, 과제 상태를 지웁니다."):
            self.session.reset_records()
            QMessageBox.information(self, "기록 초기화", "기록을 초기화했습니다.")
            self.reset_done.emit()

    def confirm_delete(self):
        if self._confirm("계정 삭제", "계정과 모든 데이터를 지웁니다."):
            self.session.delete_account()
            QMessageBox.information(self, "계정 삭제", "계정을 삭제했습니다. 계정 선택 창으로 돌아갑니다.")
            self.account_deleted.emit()
