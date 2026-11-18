#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - 클로드 스마트 보카 - 웹 서버 실행 (이 PC에서만 접속 가능, 기본 브라우저 자동 열기)
# 파일 위치: web/run.py
# 실행: 프로젝트 루트에서 python web/run.py

import threading
import webbrowser

import uvicorn

from app import create_app

HOST = "127.0.0.1"
PORT = 8765
BROWSER_DELAY_SECONDS = 1.5


def open_browser_later(url):
    timer = threading.Timer(BROWSER_DELAY_SECONDS, webbrowser.open, args=(url,))
    timer.daemon = True
    timer.start()


def main():
    url = f"http://{HOST}:{PORT}/"
    print(f"스마트 보카 웹 서버를 시작합니다: {url}")
    print("종료하려면 이 창에서 Ctrl+C를 누르세요.")
    open_browser_later(url)
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
