#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 데이터 폴더 환경 변수(SMARTVOCA_DATA_DIR) 적용 테스트
# 파일 위치: tests/test_config.py

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"


def read_base_dir_in_subprocess(extra_env):
    """config를 새 프로세스에서 불러와 BASE_DIR을 읽는다 (모듈 로드 시점 값을 보기 위해)."""
    env = {key: value for key, value in os.environ.items() if key != "SMARTVOCA_DATA_DIR"}
    env.update(extra_env)
    code = "import sys; sys.path.insert(0, sys.argv[1]); import config; print(config.BASE_DIR)"
    result = subprocess.run(
        [sys.executable, "-c", code, str(SRC_DIR)],
        capture_output=True, text=True, env=env, check=True,
    )
    return Path(result.stdout.strip())


class DataDirTests(unittest.TestCase):
    def test_default_is_project_data_folder(self):
        base_dir = read_base_dir_in_subprocess({})
        self.assertEqual(base_dir, PROJECT_DIR / "data")

    def test_environment_variable_overrides_data_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = read_base_dir_in_subprocess({"SMARTVOCA_DATA_DIR": temp_dir})
            self.assertEqual(base_dir, Path(temp_dir).resolve())

    def test_blank_environment_variable_is_ignored(self):
        base_dir = read_base_dir_in_subprocess({"SMARTVOCA_DATA_DIR": "   "})
        self.assertEqual(base_dir, PROJECT_DIR / "data")


if __name__ == "__main__":
    unittest.main()
