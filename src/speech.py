#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-21 - 클로드 스마트 보카 - Windows 내장 음성(System.Speech)으로 영단어 발음 재생 (기능 6)
# 파일 위치: src/speech.py

import re
import subprocess

SPEAKABLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]*$")
CREATE_NO_WINDOW = 0x08000000


def is_speakable(text):
    """영문 단어만 발음한다. 그 밖의 문자는 명령에 넣지 않는다."""
    return bool(SPEAKABLE_PATTERN.match(text))


def build_speak_command(word):
    """PowerShell로 System.Speech를 불러 단어를 읽는 명령 목록을 만든다. 작은따옴표는 두 번 써서 이스케이프한다."""
    safe_word = word.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$speaker.Speak('{safe_word}')"
    )
    return ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script]


def speak_word(word):
    """단어를 소리 내어 읽는다. 영문이 아니거나 실행에 실패하면 False."""
    if not is_speakable(word):
        return False
    try:
        subprocess.Popen(build_speak_command(word), creationflags=CREATE_NO_WINDOW)
    except OSError:
        return False
    return True
