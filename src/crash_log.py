#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 클로드 스마트 보카 - 처리되지 않은 오류를 로그 파일에 남기고 안내 창을 띄운다 (exe는 콘솔이 없어 오류가 안 보이므로)
# 파일 위치: src/crash_log.py

import sys
import traceback
from datetime import datetime
from pathlib import Path

from config import APP_TITLE, ERROR_LOG_PATH

LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_error(exc_type, exc_value, tb):
    """예외 종류, 메시지, 호출 경로를 한 덩어리 문자열로 만든다."""
    return "".join(traceback.format_exception(exc_type, exc_value, tb))


def write_error_log(text, log_path=ERROR_LOG_PATH):
    """시각과 함께 로그 파일 끝에 덧붙인다. 쓰기에 실패하면 False를 돌려주고 프로그램은 계속 진행한다."""
    try:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime(LOG_TIME_FORMAT)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{stamp}]\n{text}\n")
        return True
    except OSError:
        return False


def make_uncaught_handler(log_path=ERROR_LOG_PATH, show_dialog=True):
    """sys.excepthook에 넣을 함수를 만든다. show_dialog=False면 창을 띄우지 않는다 (테스트용)."""

    def handle_uncaught(exc_type, exc_value, tb):
        # Ctrl+C 같은 중단 신호는 기본 처리에 맡긴다.
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, tb)
            return

        text = format_error(exc_type, exc_value, tb)
        logged = write_error_log(text, log_path)
        if sys.stderr is not None:
            sys.stderr.write(text)

        if not show_dialog:
            return
        # 창을 띄우려면 QApplication이 있어야 한다. 아직 없으면 로그만 남긴다.
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is None:
            return
        message = "예상하지 못한 오류가 발생했습니다. 프로그램을 다시 실행해 보세요."
        if logged:
            message += f"\n\n자세한 내용은 다음 파일에 기록했습니다:\n{log_path}"
        QMessageBox.critical(None, APP_TITLE, message)

    return handle_uncaught


def install_crash_handler():
    """앱 시작 시 한 번 호출한다. 이후 잡히지 않은 예외는 로그와 안내 창으로 처리된다."""
    sys.excepthook = make_uncaught_handler()
