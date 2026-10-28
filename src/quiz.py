#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 시험 문항 생성(단답·4지선다·OX), 오답 보기 선택, 채점
# 파일 위치: src/quiz.py

import difflib
from dataclasses import dataclass, field

from config import DISTRACTOR_CANDIDATE_LIMIT, DISTRACTOR_COUNT
from vocab import entry_pos_keys

DIRECTION_EN_TO_KO = "영어→한글"
DIRECTION_KO_TO_EN = "한글→영어"
DIRECTION_MIXED = "복합"

KIND_SHORT = "단답형"
KIND_CHOICE = "4지선다형"
KIND_OX = "OX형"

OX_TRUE = "O"
OX_FALSE = "X"


@dataclass
class Question:
    """시험 문항 하나. accepted의 값 중 하나와 일치하면 정답이다."""

    word: str
    direction: str
    kind: str
    prompt: str
    accepted: list
    expected_text: str
    choices: list = field(default_factory=list)


@dataclass
class QuizResult:
    """채점 결과 한 문항."""

    word: str
    direction: str
    kind: str
    user_answer: str
    is_correct: bool
    expected_text: str


def normalize_answer(text):
    """채점용 정규화: 공백 제거, 소문자 변환."""
    return "".join(text.split()).lower()


def is_correct(question, user_answer):
    accepted_keys = {normalize_answer(answer) for answer in question.accepted}
    return normalize_answer(user_answer) in accepted_keys


def distribute_counts(total, slots):
    """전체 개수를 칸 수로 나눈다. 나머지는 앞 칸부터 1개씩 더한다."""
    base, remainder = divmod(total, slots)
    return [base + (1 if index < remainder else 0) for index in range(slots)]


def build_kind_sequence(total, kinds, rng):
    """선택한 유형을 균등 배분한 뒤 순서를 섞는다."""
    counts = distribute_counts(total, len(kinds))
    sequence = []
    for kind, count in zip(kinds, counts):
        sequence.extend([kind] * count)
    rng.shuffle(sequence)
    return sequence


def build_direction_sequence(total, direction, rng):
    """방향을 정한다. 복합이면 문항마다 영어→한글과 한글→영어를 50:50으로 섞는다."""
    if direction != DIRECTION_MIXED:
        return [direction] * total
    half = total // 2
    sequence = [DIRECTION_EN_TO_KO] * half + [DIRECTION_KO_TO_EN] * (total - half)
    rng.shuffle(sequence)
    return sequence


def display_text(entry, direction):
    """방향에 따라 보기로 쓰는 텍스트. 영어→한글이면 뜻, 한글→영어면 단어."""
    if direction == DIRECTION_EN_TO_KO:
        return entry.meanings[0]
    return entry.word


def meaning_keys(entry):
    return {normalize_answer(meaning) for meaning in entry.meanings}


def pick_distractors(target, pool, direction, rng):
    """오답 보기를 고른다.

    같은 품사만 후보로 하고, 정답과 뜻이 겹치는 단어는 뺀다.
    철자 유사도가 높은 상위 후보에서 무작위로 고른다.
    """
    target_keys = meaning_keys(target)
    target_text = normalize_answer(display_text(target, direction))
    target_pos = entry_pos_keys(target)
    same_pos, any_pos = [], []
    for entry in pool.values():
        if entry.word == target.word:
            continue
        if meaning_keys(entry) & target_keys:
            continue
        if normalize_answer(display_text(entry, direction)) == target_text:
            continue
        any_pos.append(entry)
        if entry_pos_keys(entry) & target_pos:
            same_pos.append(entry)

    candidates = same_pos if len(same_pos) >= DISTRACTOR_COUNT else any_pos
    scored = [
        (difflib.SequenceMatcher(None, target.word, entry.word).ratio(), entry)
        for entry in candidates
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].word))
    top = [entry for _, entry in scored[:DISTRACTOR_CANDIDATE_LIMIT]]
    return rng.sample(top, min(DISTRACTOR_COUNT, len(top)))


def build_short_question(target, direction):
    if direction == DIRECTION_EN_TO_KO:
        return Question(target.word, direction, KIND_SHORT, target.word,
                        list(target.meanings), " / ".join(target.meanings))
    return Question(target.word, direction, KIND_SHORT, target.meanings[0],
                    [target.word], target.word)


def build_choice_question(target, direction, pool, rng):
    distractors = pick_distractors(target, pool, direction, rng)
    correct_text = display_text(target, direction)
    choices = [correct_text] + [display_text(entry, direction) for entry in distractors]
    rng.shuffle(choices)
    prompt = target.word if direction == DIRECTION_EN_TO_KO else target.meanings[0]
    accepted = list(target.meanings) if direction == DIRECTION_EN_TO_KO else [target.word]
    return Question(target.word, direction, KIND_CHOICE, prompt, accepted,
                    correct_text, choices)


def build_ox_question(target, direction, pool, rng, is_true):
    """OX 문항. 참이면 정답 뜻을, 거짓이면 다른 단어의 뜻을 붙인다."""
    if is_true:
        shown = display_text(target, direction)
        accepted = [OX_TRUE]
    else:
        distractors = pick_distractors(target, pool, direction, rng)
        if not distractors:
            shown = display_text(target, direction)
            accepted = [OX_TRUE]
        else:
            shown = display_text(distractors[0], direction)
            accepted = [OX_FALSE]
    prompt = target.word if direction == DIRECTION_EN_TO_KO else target.meanings[0]
    expected_mark = accepted[0]
    expected_text = f"{expected_mark} ({display_text(target, direction)})"
    return Question(target.word, direction, KIND_OX, f"{prompt} = {shown}",
                    accepted, expected_text, [OX_TRUE, OX_FALSE])


def build_questions(targets, pool, direction, kinds, rng):
    """문항 목록을 만든다. targets는 WordEntry 목록, pool은 주변 보기 후보 풀(dict)이다."""
    count = len(targets)
    kind_sequence = build_kind_sequence(count, kinds, rng)
    direction_sequence = build_direction_sequence(count, direction, rng)

    ox_count = kind_sequence.count(KIND_OX)
    ox_truth = [True] * (ox_count // 2) + [False] * (ox_count - ox_count // 2)
    rng.shuffle(ox_truth)
    ox_index = 0

    questions = []
    for target, kind, question_direction in zip(targets, kind_sequence, direction_sequence):
        if kind == KIND_SHORT:
            questions.append(build_short_question(target, question_direction))
        elif kind == KIND_CHOICE:
            questions.append(build_choice_question(target, question_direction, pool, rng))
        else:
            is_true = ox_truth[ox_index]
            ox_index += 1
            questions.append(build_ox_question(target, question_direction, pool, rng, is_true))
    return questions


def grade_answers(questions, answers):
    """문항과 답 목록(같은 순서)을 채점해 결과 목록을 돌려준다."""
    results = []
    for question, answer in zip(questions, answers):
        results.append(QuizResult(
            word=question.word,
            direction=question.direction,
            kind=question.kind,
            user_answer=answer,
            is_correct=is_correct(question, answer),
            expected_text=question.expected_text,
        ))
    return results


def score_of(results):
    """정답률 (0~1). 결과가 없으면 0."""
    if not results:
        return 0.0
    return sum(1 for result in results if result.is_correct) / len(results)
