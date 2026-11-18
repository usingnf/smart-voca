#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 웹 API 시나리오를 임시 데이터 폴더에서 실행하는 래퍼 테스트
# 파일 위치: tests/test_web_api.py

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
SOURCE_VOCA = PROJECT_DIR / "data" / "voca.csv"


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"),
                     "fastapi와 httpx가 설치되어 있어야 웹 API 테스트를 실행합니다")
class WebApiIsolationTests(unittest.TestCase):
    def test_web_api_cases_pass_with_temporary_data_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 실제 학습 기록(data/users 등)을 건드리지 않도록 단어 파일만 복사해서 쓴다.
            shutil.copy(SOURCE_VOCA, Path(temp_dir) / "voca.csv")
            env = dict(os.environ, SMARTVOCA_DATA_DIR=temp_dir, PYTHONIOENCODING="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "web_api_cases"],
                cwd=TESTS_DIR, env=env, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr[-3000:])


if __name__ == "__main__":
    unittest.main()
