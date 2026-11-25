#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 시험 문제를 가중치에 따라 고르는 규칙 (안 본 단어·오답률 높은 단어·오래 안 본 단어 우선)
# 파일 위치: src/sampling.py

from datetime import date

from config import (
    TEST_STALE_DAYS,
    TEST_WEIGHT_BASE,
    TEST_WEIGHT_ERROR_RATE,
    TEST_WEIGHT_NEVER_ASKED,
    TEST_WEIGHT_STALE,
)
from daily import error_rate


def word_weight(stats, word, today):
    """단어 하나의 출제 가중치. 값이 클수록 자주 뽑힌다.

    - 출제 기록이 없으면 안 본 단어로 보고 가중치를 크게 준다.
    - 오답률이 높을수록 더한다.
    - 마지막 출제가 TEST_STALE_DAYS일 이상 지났거나 날짜가 없으면 오래된 단어로 보고 더한다.
    """
    record = stats.get(word)
    if not record or record.get("asked", 0) == 0:
        return TEST_WEIGHT_BASE + TEST_WEIGHT_NEVER_ASKED
    weight = TEST_WEIGHT_BASE + TEST_WEIGHT_ERROR_RATE * error_rate(stats, word)
    last_asked = record.get("last_asked")
    if last_asked is None or (today - date.fromisoformat(last_asked)).days >= TEST_STALE_DAYS:
        weight += TEST_WEIGHT_STALE
    return weight


def pick_weighted_words(candidates, stats, today, count, rng):
    """후보(dict: 단어 → 항목)에서 가중치에 따라 중복 없이 count개를 고른다. 반환은 항목 목록."""
    items = list(candidates.values())
    weights = [word_weight(stats, entry.word, today) for entry in items]
    picked = []
    for _ in range(min(count, len(items))):
        index = _weighted_index(weights, rng)
        picked.append(items.pop(index))
        weights.pop(index)
    return picked


def _weighted_index(weights, rng):
    """가중치 비율로 위치 하나를 고른다."""
    threshold = rng.uniform(0, sum(weights))
    running = 0.0
    for index, weight in enumerate(weights):
        running += weight
        if threshold < running:
            return index
    return len(weights) - 1
