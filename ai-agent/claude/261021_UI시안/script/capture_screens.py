#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - UI 시안의 각 메뉴 화면을 PNG로 저장 (검토용)
# 파일 위치: ai-agent/claude/261021_UI시안/script/capture_screens.py

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR / "src"))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui_mockup import MENU_ITEMS, THEME_LIGHT, MainWindow, apply_app_font, apply_theme  # noqa: E402

IMAGE_DIR = WORK_DIR / "images"


def capture_all_pages():
    """메뉴 항목마다 밝게/어둡게 두 테마의 메인 창을 저장한다."""
    app = QApplication.instance() or QApplication(sys.argv)
    apply_app_font(app)
    apply_theme(app, THEME_LIGHT)
    window = MainWindow("샘플")
    window.show()
    app.processEvents()

    for theme_suffix in ["", "_어둡게"]:
        if theme_suffix:
            window.toggle_theme()
            app.processEvents()

        for index, menu_name in enumerate(MENU_ITEMS):
            window.menu_list.setCurrentRow(index)
            app.processEvents()
            image_path = IMAGE_DIR / f"시안_{index + 1:02d}_{menu_name}{theme_suffix}.png"
            window.grab().save(str(image_path))
            print(f"saved: {image_path.name}")


if __name__ == "__main__":
    capture_all_pages()
