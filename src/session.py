#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 로그인한 사용자의 상태(과제, 통계, 기록, 즐겨찾기, 단어 풀)를 묶는 세션
# 파일 위치: src/session.py

import random
import shutil

from config import (
    RECORD_MEMORIZE,
    RECORD_TEST,
    RESULT_CORRECT,
    RESULT_OPENED,
    RESULT_WRONG,
    STATUS_MISSED,
    STATUS_PENDING,
)
from daily import complete_assignment, create_today_assignment, find_assignment
from quiz import score_of
from timeutil import kst_now, kst_today
from user_store import UserStore, make_custom_entry

TEST_RECORD_KINDS = {RECORD_TEST, "과제시험"}


class UserSession:
    """한 사용자의 모든 상태를 다룬다. 화면은 이 객체만 호출한다."""

    def __init__(self, username_key, display_name, vocabulary, rng=None):
        self.username_key = username_key
        self.display_name = display_name
        self.vocabulary = vocabulary
        self.rng = rng or random.Random()
        self.store = UserStore(username_key)
        self.store.create()
        self.state = self.store.load_state()
        self.state.setdefault("favorites", [])
        self.custom = self.store.load_custom_words()
        self.pool = self.vocabulary.merged(self.custom)

    def save(self):
        self.store.save_state(self.state)

    def refresh_pool(self):
        self.pool = self.vocabulary.merged(self.custom)

    def exists_word(self, word):
        return word in self.pool

    def is_custom_word(self, word):
        return word in self.custom

    # ----- 단어 관리 (기능 2) -----

    def add_word(self, word, pos, meanings):
        """단어를 추가한다. 이미 있으면 뜻을 합친다. 합쳤으면 True를 반환한다."""
        existing = self.pool.get(word)
        if existing is None:
            entry = make_custom_entry(word, pos, meanings)
            merged = False
        else:
            combined = list(existing.meanings)
            combined.extend(meaning for meaning in meanings if meaning not in combined)
            entry = make_custom_entry(
                word, existing.pos or pos, combined,
                synonyms=existing.synonyms, english_gloss=existing.english_gloss,
                example=existing.example,
            )
            merged = True
        self._store_custom(entry)
        return merged

    def update_custom_word(self, word, pos, meanings):
        """사용자 추가 단어의 품사와 뜻을 바꾼다."""
        current = self.custom[word]
        entry = make_custom_entry(word, pos, meanings, synonyms=current.synonyms,
                                  english_gloss=current.english_gloss, example=current.example)
        self._store_custom(entry)

    def delete_custom_word(self, word):
        """사용자 추가 단어를 지운다. 기본 단어와 같은 단어였다면 기본 뜻으로 돌아간다."""
        self.custom.pop(word, None)
        self.store.save_custom_words(self.custom)
        self.refresh_pool()
        self.state["favorites"] = [item for item in self.state["favorites"] if item != word]
        self.save()

    def _store_custom(self, entry):
        self.custom[entry.word] = entry
        self.store.save_custom_words(self.custom)
        self.refresh_pool()

    # ----- 즐겨찾기 (기능 3) -----

    def is_favorite(self, word):
        return word in self.state["favorites"]

    def toggle_favorite(self, word):
        if self.is_favorite(word):
            self.state["favorites"].remove(word)
        else:
            self.state["favorites"].append(word)
        self.save()
        return self.is_favorite(word)

    def favorite_pool(self):
        return {word: entry for word, entry in self.pool.items() if word in self.state["favorites"]}

    # ----- 과제 -----

    def today_assignment(self):
        """오늘 과제를 가져온다. 없으면 만든다."""
        assignment = create_today_assignment(self.state, kst_today(), self.pool, self.rng)
        self.save()
        return assignment

    def pending_today(self):
        """오늘 과제가 아직 완수되지 않았으면 True."""
        assignment = find_assignment(self.state, kst_today())
        return assignment is not None and assignment["status"] == STATUS_PENDING

    def finish_assignment(self, assignment, results):
        """과제 시험 결과로 완수 여부를 정한다. 통과하면 True."""
        passed = complete_assignment(assignment, score_of(results))
        self.save()
        return passed

    def abandon_assignment(self, assignment):
        """과제 시험을 끝까지 치르지 않고 나가면 미이수로 바꾸고, 단어를 다음 날 복습 대기열에 넣는다."""
        assignment["status"] = STATUS_MISSED
        for word in assignment["words"]:
            if word not in self.state["queue"]:
                self.state["queue"].append(word)
        self.save()

    # ----- 암기·시험 기록 -----

    def record_memorize(self, word):
        """암기 화면에서 단어를 열었을 때 기록한다. 오답률에는 넣지 않는다."""
        today_key = kst_today().isoformat()
        words = self.state["memorized"].setdefault(today_key, [])
        if word not in words:
            words.append(word)
        self.save()
        self.store.append_history([self._history_row(
            RECORD_MEMORIZE, word, "", "", RESULT_OPENED, "", "")])

    def record_results(self, results, kind_label):
        """시험 결과를 오답률 통계와 이력에 기록한다."""
        history_rows = []
        for result in results:
            record = self.state["stats"].setdefault(result.word, {"asked": 0, "wrong": 0})
            record["asked"] += 1
            if not result.is_correct:
                record["wrong"] += 1
            history_rows.append(self._history_row(
                kind_label, result.word, result.direction, result.kind,
                RESULT_CORRECT if result.is_correct else RESULT_WRONG,
                result.user_answer, result.expected_text,
            ))
        self.save()
        self.store.append_history(history_rows)

    def wrong_words(self):
        """가장 최근 시험에서 틀린 단어 목록 (기능 1: 오답 재시험용). 최근 기록 순서."""
        latest = {}
        for row in self.history():
            if row["구분"] in TEST_RECORD_KINDS:
                latest[row["단어"]] = row["결과"]
        return [word for word, result in latest.items() if result == RESULT_WRONG and word in self.pool]

    # ----- 계정 -----

    def reset_records(self):
        """오답률, 이력, 과제 상태를 지운다. 추가 단어와 즐겨찾기는 남긴다."""
        favorites = list(self.state.get("favorites", []))
        self.store.reset()
        self.state = self.store.load_state()
        self.state["favorites"] = favorites
        self.save()

    def delete_account(self):
        self.store.delete()

    def export_history(self, target_path):
        """이력 CSV를 지정한 경로로 복사한다. 이력이 없으면 False."""
        if not self.store.history_path.exists():
            return False
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.store.history_path, target_path)
        return True

    def history(self):
        return self.store.read_history()

    def _history_row(self, kind, word, direction, kind_of_question, result, user_input, expected):
        return {
            "일시": kst_now().isoformat(timespec="seconds"),
            "구분": kind,
            "단어": word,
            "방향": direction,
            "유형": kind_of_question,
            "결과": result,
            "입력값": user_input,
            "정답": expected,
        }
