#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - 클로드 스마트 보카 - 한국어기초사전 API로 한글 뜻의 영어 번역 보조 검색 (FR-12)
# 파일 위치: src/online_dict.py

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field

KRDICT_SEARCH_URL = "https://krdict.korean.go.kr/api/search"
KRDICT_TRANS_LANG_ENGLISH = "1"
KRDICT_RESULT_NUM = 10
REQUEST_TIMEOUT_SECONDS = 5

ATTRIBUTION_TEXT = "출처: 국립국어원 한국어기초사전 (크리에이티브 커먼즈 저작자표시-동일조건변경허락 2.0 대한민국)"

MSG_NO_KEY ="온라인 검색 인증키가 없어 건너뜁니다. settings.json의 krdict_api_key를 입력하세요."
MSG_OFFLINE = "인터넷에 연결되어 있지 않아 온라인 검색을 건너뜁니다. 로컬 결과만 표시합니다."


class OnlineDictError(Exception):
    """온라인 검색 실패. 메시지는 화면에 그대로 보여 준다."""


@dataclass
class OnlineWord:
    """온라인 사전의 표제어 한 개와 영어 번역 목록."""

    word: str
    pos: str = ""
    english: list = field(default_factory=list)


def build_search_url(api_key, query):
    """검색 요청 주소를 만든다. 한글 표제어를 찾고 영어 번역을 함께 요청한다."""
    params = {
        "key": api_key,
        "q": query,
        "part": "word",
        "translated": "y",
        "trans_lang": KRDICT_TRANS_LANG_ENGLISH,
        "num": str(KRDICT_RESULT_NUM),
    }
    return f"{KRDICT_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def parse_search_xml(xml_text):
    """응답 XML을 OnlineWord 목록으로 바꾼다. 영어 번역이 없는 항목은 버린다.

    오류 응답(<error><error_code>, <message>)은 OnlineDictError로 바꾼다.
    """
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise OnlineDictError("온라인 응답을 읽을 수 없습니다.") from error

    error_node = root if root.tag == "error" else root.find("error")
    if error_node is not None:
        code = (error_node.findtext("error_code") or "").strip()
        message = (error_node.findtext("message") or "").strip() or "알 수 없는 오류"
        title = f"온라인 검색 오류 {code}" if code else "온라인 검색 오류"
        raise OnlineDictError(f"{title}: {message}")

    results = []
    for item in root.iter("item"):
        word = (item.findtext("word") or "").strip()
        english = []
        for sense in item.findall("sense"):
            for translation in sense.findall("translation"):
                text = (translation.findtext("trans_word") or "").strip()
                if text and text not in english:
                    english.append(text)
        if word and english:
            results.append(OnlineWord(word=word, pos=(item.findtext("pos") or "").strip(), english=english))
    return results


def search_english_translations(query, api_key, timeout=REQUEST_TIMEOUT_SECONDS):
    """한글 검색어의 영어 번역을 온라인으로 찾는다.

    인증키가 없거나, 인터넷이 없거나, 시간 초과·서버 오류가 나면 OnlineDictError를 던진다.
    호출한 쪽은 이 예외를 잡아 로컬 결과만 보여 준다.
    """
    if not api_key:
        raise OnlineDictError(MSG_NO_KEY)
    url = build_search_url(api_key, query)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise OnlineDictError(f"온라인 서버 오류 (HTTP {error.code})") from error
    except (urllib.error.URLError, OSError) as error:
        raise OnlineDictError(MSG_OFFLINE) from error
    return parse_search_xml(body.decode("utf-8"))
