#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 밝게/어둡게 테마, 글꼴 크기 조절, 글꼴 단계(제목·강조) 적용
# 파일 위치: src/ui/theme.py

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QWidget

from settings import THEME_DARK, THEME_LIGHT

KOREAN_FONT_FAMILY = "Malgun Gothic"

# 글꼴 단계: 위젯에 setProperty("fontLevel", 단계명)을 주면 기본 글꼴 크기의 배수로 맞춰진다.
FONT_LEVEL_SCALE = {
    "title": 1.8,
    "emphasis": 1.4,
    "large": 2.4,
}
FONT_LEVEL_PROPERTY = "fontLevel"


def apply_app_font(app, point_size):
    """앱 전체 기본 글꼴을 맑은 고딕과 지정한 크기로 바꾼다."""
    font = QFont(KOREAN_FONT_FAMILY)
    font.setPointSize(point_size)
    app.setFont(font)


def mark_font_level(widget, level):
    """위젯의 글꼴 단계를 지정한다. 적용은 apply_font_levels()가 한다."""
    widget.setProperty(FONT_LEVEL_PROPERTY, level)


def apply_font_levels(app, root):
    """root 아래 모든 위젯에 현재 기본 글꼴 크기 기준의 단계별 글꼴을 다시 적용한다."""
    base_size = app.font().pointSizeF()
    for widget in root.findChildren(QWidget):
        level = widget.property(FONT_LEVEL_PROPERTY)
        if not level:
            continue
        font = QFont(app.font())
        font.setPointSizeF(base_size * FONT_LEVEL_SCALE[level])
        font.setBold(level in ("title", "emphasis"))
        widget.setFont(font)


def build_dark_palette():
    """어두운 배경과 밝은 글자를 쓰는 팔레트."""
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


CORRECT_COLOR_LIGHT = QColor(27, 94, 32)
WRONG_COLOR_LIGHT = QColor(183, 28, 28)
CORRECT_COLOR_DARK = QColor(129, 199, 132)
WRONG_COLOR_DARK = QColor(239, 154, 154)


def result_colors(palette):
    """정답·오답 글자색. 어두운 테마에서는 밝은 색을 쓴다."""
    is_dark = palette.window().color().lightness() < 128
    if is_dark:
        return CORRECT_COLOR_DARK, WRONG_COLOR_DARK
    return CORRECT_COLOR_LIGHT, WRONG_COLOR_LIGHT


def apply_theme(app, theme_name):
    """Fusion 스타일로 통일한 뒤 테마 팔레트를 적용한다."""
    app.setStyle("Fusion")
    if theme_name == THEME_DARK:
        app.setPalette(build_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())


__all__ = [
    "THEME_DARK", "THEME_LIGHT", "apply_app_font", "apply_font_levels",
    "apply_theme", "mark_font_level",
]
