#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 경로와 고정 설정값 (exe 실행 시 exe 옆 폴더 기준)
# 파일 위치: src/config.py

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


def resolve_base_dir():
    """exe 실행이면 exe 옆 폴더, 개발 실행이면 프로젝트의 data 폴더를 쓴다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1] / "data"


BASE_DIR = resolve_base_dir()
VOCA_PATH = BASE_DIR / "voca.csv"
USERS_DIR = BASE_DIR / "users"
REPORTS_DIR = BASE_DIR / "reports"
