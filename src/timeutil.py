#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 한국 표준시(KST) 기준 현재 시각과 날짜
# 파일 위치: src/timeutil.py

from datetime import datetime, timedelta, timezone

from config import KST_OFFSET_HOURS

KST = timezone(timedelta(hours=KST_OFFSET_HOURS))


def kst_now():
    """KST 기준 현재 시각 (timezone 정보 포함)."""
    return datetime.now(KST)


def kst_today():
    """KST 기준 오늘 날짜."""
    return kst_now().date()
