#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 진행 중인 시험 문항을 서버 메모리에 잠시 보관 (정답을 브라우저로 보내지 않기 위함)
# 파일 위치: web/quiz_registry.py

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock

MAX_OPEN_QUIZZES = 50

MODE_TEST = "test"
MODE_WRONG = "wrong"
MODE_ASSIGNMENT = "assignment"


@dataclass
class OpenQuiz:
    """서버가 들고 있는 시험 한 회분. 정답(accepted)은 여기에만 있다."""

    username: str
    mode: str
    questions: list = field(default_factory=list)


class QuizRegistry:
    """시험 문항을 id로 찾을 수 있게 보관한다. 너무 많이 쌓이면 가장 오래된 것부터 버린다."""

    def __init__(self, max_size=MAX_OPEN_QUIZZES):
        self.max_size = max_size
        self._quizzes = OrderedDict()
        self._lock = Lock()

    def add(self, username, mode, questions):
        quiz_id = uuid.uuid4().hex
        with self._lock:
            self._quizzes[quiz_id] = OpenQuiz(username=username, mode=mode, questions=list(questions))
            while len(self._quizzes) > self.max_size:
                self._quizzes.popitem(last=False)
        return quiz_id

    def get(self, quiz_id):
        with self._lock:
            return self._quizzes.get(quiz_id)

    def remove(self, quiz_id):
        with self._lock:
            self._quizzes.pop(quiz_id, None)
