#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 일일 영단어 과제 생성, 미이수 이월, 완수 판정
# 파일 위치: src/daily.py

from datetime import timedelta

from config import (
    DAILY_ASSIGNMENT_SIZE,
    PASS_RATE,
    REVIEW_RATIO_MAX,
    REVIEW_RATIO_MIN,
    STATUS_COMPLETED,
    STATUS_MISSED,
    STATUS_PENDING,
)


def error_rate(stats, word):
    """단어의 오답률 = 오답 수 / 출제 수. 출제 기록이 없으면 0."""
    record = stats.get(word)
    if not record or record["asked"] == 0:
        return 0.0
    return record["wrong"] / record["asked"]


def choose_review_count(rng):
    """복습 비율을 10~50%에서 무작위로 정하고 복습 단어 수를 반올림한다."""
    ratio = rng.uniform(REVIEW_RATIO_MIN, REVIEW_RATIO_MAX)
    return int(DAILY_ASSIGNMENT_SIZE * ratio + 0.5)


def find_assignment(state, day):
    """날짜에 해당하는 과제를 찾는다. 없으면 None."""
    day_key = day.isoformat()
    for assignment in state["assignments"]:
        if assignment["date"] == day_key:
            return assignment
    return None


def close_overdue(state):
    """완수하지 못한 과제를 미이수로 바꾸고, 그 단어를 복습 대기열 뒤에 넣는다."""
    for assignment in state["assignments"]:
        if assignment["status"] != STATUS_PENDING:
            continue
        assignment["status"] = STATUS_MISSED
        for word in assignment["words"]:
            if word not in state["queue"]:
                state["queue"].append(word)


def pick_review_words(state, yesterday_words, review_count, pool, rng):
    """복습 단어를 고른다. 대기열을 먼저 쓰고, 부족하면 전날 암기한 단어에서 무작위로 채운다."""
    review_words = []
    while state["queue"] and len(review_words) < review_count:
        word = state["queue"].pop(0)
        if word in pool and word not in review_words:
            review_words.append(word)

    if len(review_words) < review_count:
        candidates = [word for word in yesterday_words if word in pool and word not in review_words]
        rng.shuffle(candidates)
        review_words.extend(candidates[: review_count - len(review_words)])
    return review_words


def pick_new_words(state, pool, exclude, new_count, rng):
    """이전 과제에 나온 적 없는 단어를 무작위로 고른다."""
    used = {word for assignment in state["assignments"] for word in assignment["words"]}
    candidates = [word for word in pool if word not in used and word not in exclude]
    rng.shuffle(candidates)
    return candidates[:new_count]


def pick_high_error_words(state, pool, exclude, count, rng):
    """신규 단어가 모두 소진되었을 때, 오답률이 높은 단어를 복습으로 고른다."""
    candidates = [word for word in pool if word not in exclude]
    rng.shuffle(candidates)
    candidates.sort(key=lambda word: -error_rate(state["stats"], word))
    return candidates[:count]


def create_today_assignment(state, today, pool, rng):
    """오늘 과제를 만들어 state에 추가한다. 이미 있으면 그대로 반환한다.

    pool은 단어 풀(dict)이다. 과제 구성 규칙은 설계서 5장을 따른다.
    """
    existing = find_assignment(state, today)
    if existing is not None:
        return existing

    close_overdue(state)

    review_count = choose_review_count(rng)
    yesterday_key = (today - timedelta(days=1)).isoformat()
    yesterday_words = list(state["memorized"].get(yesterday_key, []))

    review_words = pick_review_words(state, yesterday_words, review_count, pool, rng)
    new_count = DAILY_ASSIGNMENT_SIZE - len(review_words)
    new_words = pick_new_words(state, pool, set(review_words), new_count, rng)

    shortage = new_count - len(new_words)
    if shortage > 0:
        taken = set(review_words) | set(new_words)
        review_words.extend(pick_high_error_words(state, pool, taken, shortage, rng))

    assignment = {
        "date": today.isoformat(),
        "words": review_words + new_words,
        "review": review_words,
        "new": new_words,
        "status": STATUS_PENDING,
        "score": None,
    }
    state["assignments"].append(assignment)
    return assignment


def complete_assignment(assignment, score):
    """과제 시험 점수(0~1)를 기록한다. 통과 기준 이상이면 완수로 바꾸고 True를 반환한다."""
    assignment["score"] = round(score, 4)
    if score >= PASS_RATE:
        assignment["status"] = STATUS_COMPLETED
        return True
    return False
