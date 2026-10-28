#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 기록 기간 필터, 집계, HTML 보고서 생성
# 파일 위치: src/report.py

import html
from datetime import datetime, timedelta

from config import (
    RECORD_ASSIGNMENT_TEST,
    RECORD_MEMORIZE,
    RECORD_TEST,
    REPORTS_DIR,
    RESULT_CORRECT,
    RESULT_WRONG,
    STATUS_COMPLETED,
    STATUS_MISSED,
    TOP_WRONG_WORDS,
)
from timeutil import kst_today

PERIOD_ALL = "전체"
PERIOD_LAST_7 = "최근 7일"
PERIOD_LAST_30 = "최근 30일"
PERIOD_CUSTOM = "기간 선택"
PERIOD_OPTIONS = [PERIOD_ALL, PERIOD_LAST_7, PERIOD_LAST_30, PERIOD_CUSTOM]
TEST_RECORD_KINDS = {RECORD_TEST, RECORD_ASSIGNMENT_TEST}


def period_range(period, today, custom_start=None, custom_end=None):
    """기간 이름을 (시작일, 끝일) 쌍으로 바꾼다. 전체면 (None, None)."""
    if period == PERIOD_LAST_7:
        return today - timedelta(days=6), today
    if period == PERIOD_LAST_30:
        return today - timedelta(days=29), today
    if period == PERIOD_CUSTOM and custom_start and custom_end:
        return custom_start, custom_end
    return None, None


def record_day(row):
    """이력 행의 날짜(KST, 날짜만)."""
    return datetime.fromisoformat(row["일시"]).date()


def filter_records(rows, start, end):
    if start is None:
        return list(rows)
    return [row for row in rows if start <= record_day(row) <= end]


def filter_assignments(assignments, start, end):
    if start is None:
        return list(assignments)
    return [
        assignment for assignment in assignments
        if start <= datetime.fromisoformat(assignment["date"]).date() <= end
    ]


def completion_rate(assignments):
    """완수 과제 ÷ (완수 + 미이수). 종료된 과제만 센다. 대상이 없으면 None."""
    completed = sum(1 for item in assignments if item["status"] == STATUS_COMPLETED)
    missed = sum(1 for item in assignments if item["status"] == STATUS_MISSED)
    total = completed + missed
    return completed / total if total else None


def memorized_count(rows):
    return len({row["단어"] for row in rows if row["구분"] == RECORD_MEMORIZE})


def top_wrong_words(rows, limit=TOP_WRONG_WORDS):
    """시험 기록의 단어별 출제·오답으로 오답률 상위 단어를 만든다.

    출제 1회 이상인 단어만 쓰고, 오답률 내림차순, 같으면 출제 많은 순.
    반환: [(단어, 출제 수, 오답 수, 오답률), ...]
    """
    asked, wrong = {}, {}
    for row in rows:
        if row["구분"] not in TEST_RECORD_KINDS:
            continue
        word = row["단어"]
        asked[word] = asked.get(word, 0) + 1
        if row["결과"] == RESULT_WRONG:
            wrong[word] = wrong.get(word, 0) + 1

    ranked = []
    for word, count in asked.items():
        wrong_count = wrong.get(word, 0)
        ranked.append((word, count, wrong_count, wrong_count / count))
    ranked.sort(key=lambda item: (-item[3], -item[1], item[0]))
    return ranked[:limit]


def build_summary(rows, assignments, start, end):
    """기간 안의 기록으로 보고서 수치를 모은다."""
    period_rows = filter_records(rows, start, end)
    period_assignments = filter_assignments(assignments, start, end)
    test_rows = [row for row in period_rows if row["구분"] in TEST_RECORD_KINDS]
    correct = sum(1 for row in test_rows if row["결과"] == RESULT_CORRECT)
    return {
        "completion_rate": completion_rate(period_assignments),
        "memorized": memorized_count(period_rows),
        "test_total": len(test_rows),
        "test_correct": correct,
        "top_wrong": top_wrong_words(period_rows),
    }


def daily_accuracy(rows, today, days=14):
    """최근 days일의 날짜별 시험 정답률. 시험이 없는 날은 None.

    반환: [("MM-DD", 정답률 또는 None), ...] (오래된 날짜가 앞에 온다)
    """
    buckets = {}
    for row in rows:
        if row["구분"] not in TEST_RECORD_KINDS:
            continue
        day = record_day(row)
        total, correct = buckets.get(day, (0, 0))
        buckets[day] = (total + 1, correct + (1 if row["결과"] == RESULT_CORRECT else 0))

    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        total, correct = buckets.get(day, (0, 0))
        series.append((day.strftime("%m-%d"), correct / total if total else None))
    return series


def format_percent(value):
    return "-" if value is None else f"{value * 100:.0f}%"


def build_html(username, period_label, summary):
    """보고서 HTML 문자열을 만든다. 사용자 입력은 모두 이스케이프한다."""
    rows_html = "".join(
        f"<tr><td>{html.escape(word)}</td><td>{asked}</td><td>{wrong}</td>"
        f"<td>{format_percent(rate)}</td></tr>"
        for word, asked, wrong, rate in summary["top_wrong"]
    ) or '<tr><td colspan="4">표시할 기록이 없습니다.</td></tr>'
    test_rate = format_percent(
        summary["test_correct"] / summary["test_total"] if summary["test_total"] else None
    )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>스마트 보카 보고서 - {html.escape(username)}</title>
<style>
body {{ font-family: "Malgun Gothic", sans-serif; margin: 32px; color: #222; }}
table {{ border-collapse: collapse; margin-top: 8px; }}
th, td {{ border: 1px solid #bbb; padding: 6px 12px; text-align: left; }}
th {{ background: #eef3fb; }}
</style></head>
<body>
<h1>스마트 보카 보고서</h1>
<p>사용자: {html.escape(username)} / 기간: {html.escape(period_label)}</p>
<ul>
<li>과제 이수율: {format_percent(summary["completion_rate"])}</li>
<li>암기한 단어 수: {summary["memorized"]}개</li>
<li>시험 정답률: {test_rate} ({summary["test_correct"]} / {summary["test_total"]})</li>
</ul>
<h2>오답률 상위 단어 (최대 {TOP_WRONG_WORDS}개)</h2>
<table>
<tr><th>단어</th><th>출제</th><th>오답</th><th>오답률</th></tr>
{rows_html}
</table>
</body>
</html>
"""


def write_report(username_key, username, period_label, summary, today=None):
    """보고서 파일을 reports 폴더에 쓰고 경로를 돌려준다."""
    day = today or kst_today()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{username_key}_{day.isoformat()}.html"
    path.write_text(build_html(username, period_label, summary), encoding="utf-8")
    return path
