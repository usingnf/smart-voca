#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 웹 브라우저용 API와 화면 파일 제공 (업무 로직은 src 모듈을 그대로 사용)
# 파일 위치: web/app.py

import os
import sys
from dataclasses import asdict, replace
from datetime import date
from urllib.parse import quote
from pathlib import Path
from typing import List, Optional

WEB_DIR = Path(__file__).resolve().parent
SRC_DIR = WEB_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from config import (  # noqa: E402
    APP_TITLE, BASE_DIR, DAILY_ASSIGNMENT_SIZE, EXAM_QUESTION_MAX, EXAM_QUESTION_MIN, EXAM_QUESTION_STEP,
    PASS_RATE, POS_DEFAULT_ORDER, RECORD_ASSIGNMENT_TEST, RECORD_TEST, STATUS_PENDING, VOCA_PATH,
)
from online_dict import ATTRIBUTION_TEXT, MSG_NO_KEY, OnlineDictError, search_english_translations  # noqa: E402
from quiz import (  # noqa: E402
    DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN, DIRECTION_MIXED, KIND_CHOICE, KIND_OX, KIND_SHORT,
    build_questions, grade_answers, score_of,
)
from report import (  # noqa: E402
    PERIOD_CUSTOM, PERIOD_OPTIONS, build_summary, daily_accuracy, period_range,
)
from session import UserSession  # noqa: E402
from settings import THEME_CHOICES, load_settings, save_settings  # noqa: E402
from timeutil import kst_today  # noqa: E402
from user_store import UserStore, history_csv_bytes, list_user_keys, normalize_username, user_exists  # noqa: E402
from vocab import (  # noqa: E402
    POS_LABELS, WORD_PATTERN, Vocabulary, filter_by_pos, search_by_english, search_by_meaning,
)
from quiz_registry import MODE_ASSIGNMENT, MODE_TEST, MODE_WRONG, QuizRegistry  # noqa: E402

QUIZ_KINDS = [KIND_SHORT, KIND_CHOICE, KIND_OX]
QUIZ_DIRECTIONS = [DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN, DIRECTION_MIXED]
SEARCH_LIMIT = 20
MSG_OFFLINE_OFF = "온라인 검색이 꺼져 있습니다. 옵션에서 켤 수 있습니다."


def load_allowed_hosts():
    """허용할 Host 이름 목록. testserver는 자동 시험(TestClient)용이다.

    서버 배포 시에는 환경 변수 ALLOWED_HOSTS(쉼표로 구분)에 접속 주소를 더한다.
    예: ALLOWED_HOSTS=example.school.ac.kr
    """
    base_hosts = ["127.0.0.1", "localhost", "testserver"]
    extra_hosts = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "").split(",") if host.strip()]
    return base_hosts + extra_hosts


ALLOWED_HOSTS = load_allowed_hosts()


# ----- 요청 형식 -----

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class WordCreate(BaseModel):
    username: str
    word: str
    pos: str
    meanings: List[str]


class WordUpdate(BaseModel):
    username: str
    pos: str
    meanings: List[str]


class UserRef(BaseModel):
    username: str


class MemorizeOpen(BaseModel):
    username: str
    word: str


class TestQuizStart(BaseModel):
    username: str
    count: int = EXAM_QUESTION_MIN
    kinds: List[str] = Field(default_factory=lambda: list(QUIZ_KINDS))
    pos_keys: List[str] = Field(default_factory=lambda: list(POS_DEFAULT_ORDER))
    direction: str = DIRECTION_EN_TO_KO
    favorites_only: bool = False


class WrongQuizStart(BaseModel):
    username: str
    kinds: List[str] = Field(default_factory=lambda: list(QUIZ_KINDS))
    direction: str = DIRECTION_EN_TO_KO


class AssignmentQuizStart(BaseModel):
    username: str


class GradeInput(BaseModel):
    answers: List[str]


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    font_size: Optional[int] = None
    exam_count: Optional[int] = None
    exam_direction: Optional[str] = None
    memorize_direction: Optional[str] = None
    online_lookup_enabled: Optional[bool] = None
    exam_kinds: Optional[List[str]] = None
    exam_pos_keys: Optional[List[str]] = None
    exam_favorites_only: Optional[bool] = None
    krdict_api_key: Optional[str] = None


# ----- 공통 도움 함수 -----

def open_session(vocabulary, raw_username):
    """계정 이름을 확인하고 기존 계정의 세션을 연다. 계정을 새로 만들지는 않는다."""
    key = normalize_username(raw_username)
    if key is None:
        raise HTTPException(400, "사용자명은 영문·숫자·한글 1~20자로 입력하세요.")
    if not user_exists(key):
        raise HTTPException(404, "계정을 찾을 수 없습니다. 계정을 먼저 만드세요.")
    return UserSession(key, key, vocabulary)


def entry_json(session, entry):
    return {
        "word": entry.word,
        "pos": entry.pos,
        "pos_label": POS_LABELS.get(entry.pos, entry.pos),
        "meanings": entry.meanings,
        "english_gloss": entry.english_gloss,
        "synonyms": entry.synonyms,
        "example": entry.example,
        "source": entry.source,
        "license": entry.license,
        "custom": session.is_custom_word(entry.word),
        "favorite": session.is_favorite(entry.word),
    }


def question_json(index, question):
    """화면에 보내도 되는 문항 정보만 담는다. 정답(accepted, expected_text)은 제외한다."""
    return {
        "index": index,
        "word": question.word,
        "direction": question.direction,
        "kind": question.kind,
        "prompt": question.prompt,
        "choices": question.choices,
    }


def check_quiz_options(kinds, direction, pos_keys=None):
    if not kinds or any(kind not in QUIZ_KINDS for kind in kinds):
        raise HTTPException(400, "문제 유형을 하나 이상 고르세요.")
    if direction not in QUIZ_DIRECTIONS:
        raise HTTPException(400, "시험 방향이 올바르지 않습니다.")
    if pos_keys is not None and (not pos_keys or any(key not in POS_DEFAULT_ORDER for key in pos_keys)):
        raise HTTPException(400, "출제할 품사를 하나 이상 고르세요.")


def quiz_response(quiz_id, title, questions):
    return {
        "quiz_id": quiz_id,
        "title": title,
        "total": len(questions),
        "questions": [question_json(index, question) for index, question in enumerate(questions)],
    }


# ----- 앱 만들기 -----

def create_app():
    if not VOCA_PATH.exists():
        raise RuntimeError(f"단어 파일을 찾을 수 없습니다: {VOCA_PATH}")
    vocabulary = Vocabulary.load(VOCA_PATH)
    quizzes = QuizRegistry()
    app = FastAPI(title=APP_TITLE)
    # 이 PC의 주소로 온 요청만 받는다. 다른 웹페이지가 DNS 재연결로 로컬 서버를 부르는 것을 막는다.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

    # ----- 화면과 기본 정보 -----

    @app.get("/")
    def index_page():
        return FileResponse(WEB_DIR / "static" / "index.html")

    @app.get("/api/meta")
    def meta():
        return {
            "title": APP_TITLE,
            "data_dir": str(BASE_DIR),
            "word_count": len(vocabulary),
            "pos_order": POS_DEFAULT_ORDER,
            "pos_labels": POS_LABELS,
            "kinds": QUIZ_KINDS,
            "directions": QUIZ_DIRECTIONS,
            "themes": THEME_CHOICES,
            "exam_count": {"min": EXAM_QUESTION_MIN, "max": EXAM_QUESTION_MAX, "step": EXAM_QUESTION_STEP},
            "period_options": PERIOD_OPTIONS,
            "pass_rate": PASS_RATE,
            "daily_size": DAILY_ASSIGNMENT_SIZE,
            "attribution": ATTRIBUTION_TEXT,
        }

    # ----- 계정 -----

    @app.get("/api/users")
    def list_users():
        return [{"key": key} for key in list_user_keys()]

    @app.post("/api/users")
    def create_user(body: UserCreate):
        key = normalize_username(body.name)
        if key is None:
            raise HTTPException(400, "사용자명은 영문·숫자·한글 1~20자로 입력하세요.")
        existed = user_exists(key)
        UserStore(key).create()
        return {"key": key, "created": not existed}

    @app.delete("/api/users/{key}")
    def delete_user(key: str):
        session = open_session(vocabulary, key)
        session.delete_account()
        return {"ok": True}

    @app.post("/api/users/{key}/reset")
    def reset_user(key: str):
        session = open_session(vocabulary, key)
        session.reset_records()
        return {"ok": True}

    # ----- 단어 -----

    @app.get("/api/words/search")
    def search_words(username: str, q: str, mode: str = "english"):
        session = open_session(vocabulary, username)
        query = q.strip()
        if not query:
            return []
        if mode == "english":
            found = search_by_english(session.pool, query)
        elif mode == "meaning":
            found = search_by_meaning(session.pool, query, limit=SEARCH_LIMIT)
        else:
            raise HTTPException(400, "검색 방식은 english 또는 meaning입니다.")
        return [entry_json(session, entry) for entry in found]

    @app.get("/api/words/{word}")
    def get_word(word: str, username: str):
        session = open_session(vocabulary, username)
        entry = session.pool.get(word)
        if entry is None:
            raise HTTPException(404, "단어를 찾을 수 없습니다.")
        return entry_json(session, entry)

    @app.post("/api/words")
    def add_word(body: WordCreate):
        session = open_session(vocabulary, body.username)
        word = body.word.strip().lower()
        meanings = [meaning.strip() for meaning in body.meanings if meaning.strip()]
        if not WORD_PATTERN.match(word):
            raise HTTPException(400, "영단어는 영문자, 공백, 하이픈, 작은따옴표만 쓸 수 있습니다.")
        if body.pos not in POS_DEFAULT_ORDER:
            raise HTTPException(400, "품사가 올바르지 않습니다.")
        if not meanings:
            raise HTTPException(400, "한글 뜻을 한 개 이상 입력하세요.")
        existed = session.exists_word(word)
        session.add_word(word, body.pos, meanings)
        return {"word": word, "merged": existed}

    @app.put("/api/words/{word}")
    def update_word(word: str, body: WordUpdate):
        session = open_session(vocabulary, body.username)
        if not session.is_custom_word(word):
            raise HTTPException(400, "기본 단어는 수정할 수 없습니다. 추가한 단어만 수정할 수 있습니다.")
        meanings = [meaning.strip() for meaning in body.meanings if meaning.strip()]
        if body.pos not in POS_DEFAULT_ORDER or not meanings:
            raise HTTPException(400, "품사와 한글 뜻을 확인하세요.")
        session.update_custom_word(word, body.pos, meanings)
        return {"ok": True}

    @app.delete("/api/words/{word}")
    def delete_word(word: str, username: str):
        session = open_session(vocabulary, username)
        if not session.is_custom_word(word):
            raise HTTPException(400, "기본 단어는 삭제할 수 없습니다.")
        session.delete_custom_word(word)
        return {"ok": True}

    @app.post("/api/favorites/{word}")
    def toggle_favorite(word: str, body: UserRef):
        session = open_session(vocabulary, body.username)
        if word not in session.pool:
            raise HTTPException(404, "단어를 찾을 수 없습니다.")
        return {"favorite": session.toggle_favorite(word)}

    @app.get("/api/online-search")
    def online_search(username: str, q: str):
        open_session(vocabulary, username)
        settings = load_settings()
        if not settings.online_lookup_enabled:
            return {"enabled": False, "results": [], "message": MSG_OFFLINE_OFF}
        query = q.strip()
        if not query:
            return {"enabled": True, "results": [], "message": ""}
        if not settings.krdict_api_key:
            return {"enabled": True, "results": [], "message": MSG_NO_KEY}
        try:
            found = search_english_translations(query, settings.krdict_api_key)
        except OnlineDictError as error:
            return {"enabled": True, "results": [], "message": str(error)}
        return {"enabled": True, "results": [asdict(item) for item in found], "message": ""}

    # ----- 암기 -----

    @app.get("/api/memorize/next")
    def memorize_next(username: str, favorites_only: bool = False):
        session = open_session(vocabulary, username)
        notice = ""
        candidates = list(session.pool.values())
        if favorites_only:
            favorite_pool = session.favorite_pool()
            if favorite_pool:
                candidates = list(favorite_pool.values())
            else:
                notice = "즐겨찾기 단어가 없어 전체 단어에서 보여 줍니다."
        entry = session.rng.choice(candidates)
        return {"word": entry_json(session, entry), "notice": notice}

    @app.post("/api/memorize/open")
    def memorize_open(body: MemorizeOpen):
        session = open_session(vocabulary, body.username)
        if body.word not in session.pool:
            raise HTTPException(404, "단어를 찾을 수 없습니다.")
        session.record_memorize(body.word)
        return {"ok": True}

    # ----- 시험 -----

    @app.post("/api/test/quiz")
    def start_test(body: TestQuizStart):
        session = open_session(vocabulary, body.username)
        check_quiz_options(body.kinds, body.direction, body.pos_keys)
        if not (EXAM_QUESTION_MIN <= body.count <= EXAM_QUESTION_MAX) or body.count % EXAM_QUESTION_STEP:
            raise HTTPException(
                400, f"문항 수는 {EXAM_QUESTION_MIN}~{EXAM_QUESTION_MAX} 사이에서 {EXAM_QUESTION_STEP}문항 단위로 고르세요.",
            )
        # 보기(오답 후보)는 전체 풀에서 고르고, 정답 단어만 선택한 조건으로 제한한다 (화면과 같은 규칙).
        candidates = filter_by_pos(session.pool, body.pos_keys)
        if body.favorites_only:
            candidates = {word: entry for word, entry in candidates.items() if session.is_favorite(word)}
        candidate_list = list(candidates.values())
        if not candidate_list:
            raise HTTPException(400, "조건에 맞는 단어가 없습니다. 품사나 즐겨찾기 조건을 확인하세요.")
        count = min(body.count, len(candidate_list))
        targets = session.rng.sample(candidate_list, count)
        questions = build_questions(targets, session.pool, body.direction, body.kinds, session.rng)
        quiz_id = quizzes.add(session.username_key, MODE_TEST, questions)
        return quiz_response(quiz_id, "시험", questions)

    @app.post("/api/test/wrong")
    def start_wrong_test(body: WrongQuizStart):
        session = open_session(vocabulary, body.username)
        check_quiz_options(body.kinds, body.direction)
        words = [word for word in session.wrong_words() if word in session.pool]
        if not words:
            raise HTTPException(400, "최근 시험에서 틀린 단어가 없습니다.")
        targets = [session.pool[word] for word in words]
        questions = build_questions(targets, session.pool, body.direction, body.kinds, session.rng)
        quiz_id = quizzes.add(session.username_key, MODE_WRONG, questions)
        return quiz_response(quiz_id, "오답 재시험", questions)

    @app.post("/api/quiz/{quiz_id}/grade")
    def grade_quiz(quiz_id: str, body: GradeInput):
        record = quizzes.get(quiz_id)
        if record is None:
            raise HTTPException(404, "진행 중인 시험을 찾을 수 없습니다. 시험을 다시 시작하세요.")
        if len(body.answers) != len(record.questions):
            raise HTTPException(400, f"답은 {len(record.questions)}개여야 합니다.")
        session = open_session(vocabulary, record.username)
        results = grade_answers(record.questions, body.answers)
        passed = None
        if record.mode == MODE_ASSIGNMENT:
            session.record_results(results, RECORD_ASSIGNMENT_TEST)
            passed = session.finish_assignment(session.today_assignment(), results)
        else:
            session.record_results(results, RECORD_TEST)
        quizzes.remove(quiz_id)
        return {
            "score": score_of(results),
            "passed": passed,
            "pass_rate": PASS_RATE,
            "results": [
                {
                    "word": result.word,
                    "direction": result.direction,
                    "kind": result.kind,
                    "user_answer": result.user_answer,
                    "is_correct": result.is_correct,
                    "expected_text": result.expected_text,
                }
                for result in results
            ],
        }

    @app.post("/api/quiz/{quiz_id}/abort")
    def abort_quiz(quiz_id: str):
        record = quizzes.get(quiz_id)
        if record is None:
            return {"ok": True}
        if record.mode == MODE_ASSIGNMENT:
            session = open_session(vocabulary, record.username)
            session.abandon_assignment(session.today_assignment())
        quizzes.remove(quiz_id)
        return {"ok": True}

    # ----- 과제 -----

    @app.get("/api/assignment")
    def get_assignment(username: str):
        session = open_session(vocabulary, username)
        assignment = session.today_assignment()
        words = [session.pool[word] for word in assignment["words"] if word in session.pool]
        return {
            "date": assignment["date"],
            "status": assignment["status"],
            "score": assignment["score"],
            "pending": assignment["status"] == STATUS_PENDING,
            "review_count": len(assignment["review"]),
            "new_count": len(assignment["new"]),
            "words": [entry_json(session, entry) for entry in words],
        }

    @app.post("/api/assignment/quiz")
    def start_assignment(body: AssignmentQuizStart):
        session = open_session(vocabulary, body.username)
        assignment = session.today_assignment()
        if assignment["status"] != STATUS_PENDING:
            raise HTTPException(400, "오늘 과제는 이미 처리되었습니다.")
        targets = [session.pool[word] for word in assignment["words"] if word in session.pool]
        questions = build_questions(targets, session.pool, DIRECTION_MIXED, QUIZ_KINDS, session.rng)
        quiz_id = quizzes.add(session.username_key, MODE_ASSIGNMENT, questions)
        return quiz_response(quiz_id, "과제 시험", questions)

    # ----- 기록과 보고서 -----

    @app.get("/api/history")
    def get_history(username: str):
        session = open_session(vocabulary, username)
        return session.history()

    @app.get("/api/history/export")
    def export_history(username: str):
        session = open_session(vocabulary, username)
        rows = session.history()
        if not rows:
            raise HTTPException(404, "저장된 이력이 없습니다.")
        filename = f"{session.username_key}_history.csv"
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        return Response(content=history_csv_bytes(rows), media_type="text/csv", headers=headers)

    @app.get("/api/report")
    def get_report(
        username: str,
        period: str = "전체",
        start: Optional[str] = Query(default=None),
        end: Optional[str] = Query(default=None),
    ):
        session = open_session(vocabulary, username)
        if period not in PERIOD_OPTIONS:
            raise HTTPException(400, "기간 선택이 올바르지 않습니다.")
        custom_start = custom_end = None
        if period == PERIOD_CUSTOM:
            try:
                custom_start, custom_end = date.fromisoformat(start), date.fromisoformat(end)
            except (TypeError, ValueError):
                raise HTTPException(400, "직접 지정 기간은 시작일과 끝일(YYYY-MM-DD)을 함께 보내야 합니다.")
            if custom_start > custom_end:
                raise HTTPException(400, "시작일이 끝일보다 늦습니다.")
        today = kst_today()
        period_start, period_end = period_range(period, today, custom_start, custom_end)
        rows = session.history()
        summary = build_summary(rows, session.state["assignments"], period_start, period_end)
        test_total, test_correct = summary["test_total"], summary["test_correct"]
        return {
            "period": period,
            "start": period_start.isoformat() if period_start else None,
            "end": period_end.isoformat() if period_end else None,
            "completion_rate": summary["completion_rate"],
            "memorized": summary["memorized"],
            "test_total": test_total,
            "test_correct": test_correct,
            "accuracy": (test_correct / test_total) if test_total else None,
            "top_wrong": [
                {"word": word, "asked": asked, "wrong": wrong, "rate": rate}
                for word, asked, wrong, rate in summary["top_wrong"]
            ],
            "daily": [{"label": label, "rate": rate} for label, rate in daily_accuracy(rows, today)],
        }

    # ----- 옵션 -----

    @app.get("/api/settings")
    def get_settings():
        settings = load_settings()
        data = asdict(settings)
        data["krdict_api_key_set"] = bool(data.pop("krdict_api_key"))
        return data

    @app.put("/api/settings")
    def update_settings(body: SettingsUpdate):
        current = load_settings()
        updates = body.model_dump(exclude_none=True)
        settings = replace(current, **updates).sanitized() if updates else current
        save_settings(settings)
        return {"ok": True}

    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    return app
