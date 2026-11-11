#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 경로와 고정 설정값 (exe 실행 시 exe 옆 폴더 기준)
# 파일 위치: src/config.py

import os
import sys
from pathlib import Path

APP_TITLE = "스마트 보카"

# 날짜 기준: 한국 표준시 (UTC+9)
KST_OFFSET_HOURS = 9

# 일일 과제
DAILY_ASSIGNMENT_SIZE = 20
REVIEW_RATIO_MIN = 0.10
REVIEW_RATIO_MAX = 0.50
PASS_RATE = 0.80

# 시험
EXAM_QUESTION_DEFAULT = 20
EXAM_QUESTION_MIN = 5
EXAM_QUESTION_MAX = 50
EXAM_QUESTION_STEP = 5
DISTRACTOR_COUNT = 3
DISTRACTOR_CANDIDATE_LIMIT = 10

# 보고서
TOP_WRONG_WORDS = 10

# 품사 표시 순서 (키: noun, verb, adj, adv, other)
POS_DEFAULT_ORDER = ["noun", "verb", "adj", "adv", "other"]

# 계정
USERNAME_PATTERN = r"^[0-9A-Za-z가-힣]{1,20}$"

# 과제 상태
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_MISSED = "missed"

# 기록 구분
RECORD_MEMORIZE = "암기"
RECORD_TEST = "시험"
RECORD_ASSIGNMENT_TEST = "과제시험"

# 기록 결과
RESULT_OPENED = "열람"
RESULT_CORRECT = "정답"
RESULT_WRONG = "오답"

# 시험으로 치는 기록 구분 (보고서·정답률 집계에 쓴다)
TEST_RECORD_KINDS = frozenset({RECORD_TEST, RECORD_ASSIGNMENT_TEST})


def resolve_base_dir():
    """exe 실행이면 exe 옆 폴더, 개발 실행이면 프로젝트의 data 폴더를 쓴다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1] / "data"


BASE_DIR = resolve_base_dir()
VOCA_PATH = BASE_DIR / "voca.csv"

def resource_path(relative_path):
    """코드와 함께 들어가는 읽기 전용 자원(아이콘 등)의 경로.

    exe로 빌드하면 PyInstaller가 푼 임시 폴더(_MEIPASS)에 들어 있다.
    사용자 데이터(voca.csv, 이력 등)는 이 함수를 쓰지 않고 BASE_DIR을 쓴다.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


# 앱 아이콘: 제목 표시줄·작업표시줄 아이콘으로 쓴다. exe 파일 아이콘은 빌드 시 --icon으로 넣는다.
APP_ICON_PATH = resource_path("assets/SmartVoca.ico")
# 작업표시줄에서 이 앱을 파이썬과 별개의 앱으로 묶는 식별자 (Windows 전용)
APP_USER_MODEL_ID = "SmartVoca.Desktop"
USERS_DIR = BASE_DIR / "users"
REPORTS_DIR = BASE_DIR / "reports"

# 처리되지 않은 오류 기록. exe 옆에 파일을 늘리지 않으려고 사용자 로컬 앱 데이터 폴더에 둔다.
ERROR_LOG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SmartVoca" / "error.log"
