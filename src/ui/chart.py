#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 날짜별 정답률을 보여 주는 막대 그래프 위젯 (기능 4)
# 파일 위치: src/ui/chart.py

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

BAR_GAP_RATIO = 0.35
AXIS_LEFT = 40
AXIS_BOTTOM = 34
TOP_MARGIN = 12


class BarChart(QWidget):
    """라벨과 값(0~1 또는 None) 목록을 막대로 그린다. None은 빈 막대(데이터 없음)로 표시한다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.empty_text = "표시할 데이터가 없습니다."
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_items(self, items):
        self.items = list(items)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        text_color = self.palette().text().color()
        bar_color = self.palette().highlight().color()
        grid_color = QColor(text_color)
        grid_color.setAlpha(60)

        area = QRectF(AXIS_LEFT, TOP_MARGIN, self.width() - AXIS_LEFT - 8,
                      self.height() - TOP_MARGIN - AXIS_BOTTOM)
        painter.setPen(QPen(text_color))
        if not self.items or area.width() <= 0:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            painter.end()
            return

        for percent in (0, 50, 100):
            y = area.bottom() - area.height() * percent / 100
            painter.setPen(QPen(grid_color))
            painter.drawLine(int(area.left()), int(y), int(area.right()), int(y))
            painter.setPen(QPen(text_color))
            painter.drawText(QRectF(0, y - 9, AXIS_LEFT - 6, 18),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{percent}%")

        slot = area.width() / len(self.items)
        bar_width = slot * (1 - BAR_GAP_RATIO)
        metrics = QFontMetrics(self.font())
        for index, (label, value) in enumerate(self.items):
            x = area.left() + slot * index + (slot - bar_width) / 2
            if value is not None:
                height = area.height() * max(0.0, min(1.0, value))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(bar_color)
                painter.drawRect(QRectF(x, area.bottom() - height, bar_width, height))
            painter.setPen(QPen(text_color))
            label_text = metrics.elidedText(label, Qt.TextElideMode.ElideRight, int(slot))
            painter.drawText(QRectF(area.left() + slot * index, area.bottom() + 4, slot, AXIS_BOTTOM - 4),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label_text)
        painter.end()
