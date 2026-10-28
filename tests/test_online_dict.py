#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - 클로드 스마트 보카 - 온라인 한영 보조 검색(FR-12) 요청 주소, 응답 해석, 오프라인 처리 단위 테스트
# 파일 위치: tests/test_online_dict.py

import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from online_dict import (  # noqa: E402
    ATTRIBUTION_TEXT,
    KRDICT_SEARCH_URL,
    MSG_NO_KEY,
    MSG_OFFLINE,
    OnlineDictError,
    build_search_url,
    parse_search_xml,
    search_english_translations,
)
from settings import AppSettings  # noqa: E402

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<channel>
  <total>2</total>
  <item>
    <word>사과</word>
    <pos>명사</pos>
    <sense>
      <sense_order>1</sense_order>
      <definition>사과나무의 열매</definition>
      <translation><trans_lang>영어</trans_lang><trans_word>apple</trans_word></translation>
    </sense>
    <sense>
      <sense_order>2</sense_order>
      <definition>사과나무의 열매를 먹는 것</definition>
      <translation><trans_lang>영어</trans_lang><trans_word>apple</trans_word></translation>
    </sense>
  </item>
  <item>
    <word>가나다</word>
    <pos>명사</pos>
    <sense>
      <definition>번역이 없는 항목</definition>
    </sense>
  </item>
</channel>
"""


class BuildSearchUrlTest(unittest.TestCase):
    def test_url_contains_english_translation_request(self):
        url = build_search_url("KEY123", "사과")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertTrue(url.startswith(KRDICT_SEARCH_URL))
        self.assertEqual(query["key"], ["KEY123"])
        self.assertEqual(query["q"], ["사과"])
        self.assertEqual(query["part"], ["word"])
        self.assertEqual(query["translated"], ["y"])
        self.assertEqual(query["trans_lang"], ["1"])


class ParseSearchXmlTest(unittest.TestCase):
    def test_extracts_english_translations_without_duplicates(self):
        results = parse_search_xml(SAMPLE_XML)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].word, "사과")
        self.assertEqual(results[0].pos, "명사")
        self.assertEqual(results[0].english, ["apple"])

    def test_skips_items_without_translation(self):
        results = parse_search_xml(SAMPLE_XML)
        self.assertNotIn("가나다", [item.word for item in results])

    def test_empty_channel_gives_empty_list(self):
        self.assertEqual(parse_search_xml("<channel><total>0</total></channel>"), [])

    def test_broken_xml_raises_online_error(self):
        with self.assertRaises(OnlineDictError):
            parse_search_xml("<channel><item>")

    def test_error_response_raises_online_error(self):
        error_xml = "<error><error_code>020</error_code><message>Unregistered key </message></error>"
        with self.assertRaises(OnlineDictError) as context:
            parse_search_xml(error_xml)
        self.assertEqual(str(context.exception), "온라인 검색 오류 020: Unregistered key")


class SearchEnglishTranslationsTest(unittest.TestCase):
    def test_missing_key_is_reported_without_network_call(self):
        with mock.patch("online_dict.urllib.request.urlopen") as fake_open:
            with self.assertRaises(OnlineDictError) as context:
                search_english_translations("사과", "")
        fake_open.assert_not_called()
        self.assertEqual(str(context.exception), MSG_NO_KEY)

    def test_offline_gives_offline_message(self):
        with mock.patch("online_dict.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("no network")):
            with self.assertRaises(OnlineDictError) as context:
                search_english_translations("사과", "KEY")
        self.assertEqual(str(context.exception), MSG_OFFLINE)

    def test_timeout_is_treated_as_offline(self):
        with mock.patch("online_dict.urllib.request.urlopen", side_effect=TimeoutError()):
            with self.assertRaises(OnlineDictError) as context:
                search_english_translations("사과", "KEY")
        self.assertEqual(str(context.exception), MSG_OFFLINE)

    def test_http_error_gives_server_error_message(self):
        http_error = urllib.error.HTTPError(KRDICT_SEARCH_URL, 500, "Server Error", None, None)
        with mock.patch("online_dict.urllib.request.urlopen", side_effect=http_error):
            with self.assertRaises(OnlineDictError) as context:
                search_english_translations("사과", "KEY")
        self.assertIn("500", str(context.exception))

    def test_successful_response_is_parsed(self):
        fake_response = mock.MagicMock()
        fake_response.__enter__.return_value.read.return_value = SAMPLE_XML.encode("utf-8")
        with mock.patch("online_dict.urllib.request.urlopen", return_value=fake_response) as fake_open:
            results = search_english_translations("사과", "KEY")
        self.assertEqual(results[0].english, ["apple"])
        self.assertEqual(fake_open.call_args.kwargs["timeout"], 5)


class AttributionTest(unittest.TestCase):
    def test_attribution_names_source_and_license(self):
        self.assertIn("한국어기초사전", ATTRIBUTION_TEXT)
        self.assertIn("저작자표시-동일조건변경허락 2.0 대한민국", ATTRIBUTION_TEXT)


class SettingsKeyTest(unittest.TestCase):
    def test_key_is_stripped_and_kept(self):
        settings = AppSettings(krdict_api_key="  ABC  ").sanitized()
        self.assertEqual(settings.krdict_api_key, "ABC")

    def test_default_key_is_empty(self):
        self.assertEqual(AppSettings().krdict_api_key, "")


if __name__ == "__main__":
    unittest.main()
