#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - 옵션(테마, 글꼴 크기, 시험·암기 기본값) 읽기·저장
# 파일 위치: src/settings.py

import json
from dataclasses import asdict, dataclass

from config import BASE_DIR, EXAM_QUESTION_DEFAULT, EXAM_QUESTION_MAX, EXAM_QUESTION_MIN, EXAM_QUESTION_STEP
from quiz import DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN, DIRECTION_MIXED

SETTINGS_PATH = BASE_DIR / "settings.json"

THEME_LIGHT = "밝게"
THEME_DARK = "어둡게"
THEME_CHOICES = [THEME_LIGHT, THEME_DARK]

FONT_SIZE_MIN = 9
FONT_SIZE_MAX = 16
FONT_SIZE_DEFAULT = 10

DIRECTION_CHOICES = [DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN, DIRECTION_MIXED]


@dataclass
class AppSettings:
    """앱 전체 옵션. 계정과 무관하게 exe 옆 settings.json에 저장한다."""

    theme: str = THEME_LIGHT
    font_size: int = FONT_SIZE_DEFAULT
    exam_count: int = EXAM_QUESTION_DEFAULT
    exam_direction: str = DIRECTION_EN_TO_KO
    memorize_direction: str = DIRECTION_EN_TO_KO
    window_width: int = 900
    window_height: int = 600
    krdict_api_key: str = ""
    online_lookup_enabled: bool = True

    def sanitized(self):
        """범위를 벗어난 값을 기본값으로 되돌린다."""
        theme = self.theme if self.theme in THEME_CHOICES else THEME_LIGHT
        font_size = min(max(int(self.font_size), FONT_SIZE_MIN), FONT_SIZE_MAX)
        exam_count = int(self.exam_count)
        exam_count = min(max(exam_count, EXAM_QUESTION_MIN), EXAM_QUESTION_MAX)
        exam_count -= (exam_count - EXAM_QUESTION_MIN) % EXAM_QUESTION_STEP
        exam_direction = self.exam_direction if self.exam_direction in DIRECTION_CHOICES else DIRECTION_EN_TO_KO
        memorize_direction = (self.memorize_direction
                              if self.memorize_direction in (DIRECTION_EN_TO_KO, DIRECTION_KO_TO_EN)
                              else DIRECTION_EN_TO_KO)
        window_width = min(max(int(self.window_width), 800), 2560)
        window_height = min(max(int(self.window_height), 540), 1600)
        krdict_api_key = str(self.krdict_api_key or "").strip()
        online_lookup_enabled = bool(self.online_lookup_enabled)
        return AppSettings(theme, font_size, exam_count, exam_direction, memorize_direction,
                           window_width, window_height, krdict_api_key, online_lookup_enabled)


def load_settings(path=SETTINGS_PATH):
    """설정 파일을 읽는다. 없거나 깨졌으면 기본값을 쓴다."""
    if not path.exists():
        return AppSettings()
    try:
        with path.open(encoding="utf-8") as json_file:
            data = json.load(json_file)
        known = {key: value for key, value in data.items() if key in AppSettings.__dataclass_fields__}
        return AppSettings(**known).sanitized()
    except (OSError, ValueError, TypeError):
        from user_store import quarantine_file
        quarantine_file(path)
        return AppSettings()


def save_settings(settings, path=SETTINGS_PATH):
    """설정을 임시 파일에 쓴 뒤 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as json_file:
        json.dump(asdict(settings.sanitized()), json_file, ensure_ascii=False, indent=2)
    temp_path.replace(path)
