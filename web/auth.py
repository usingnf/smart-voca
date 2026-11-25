#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-26 - 클로드 스마트 보카 - 웹 로그인: 비밀번호 해시(PBKDF2), 서명된 세션 쿠키, 세션 키 준비 (표준 라이브러리만 사용)
# 파일 위치: web/auth.py

import base64
import hashlib
import hmac
import os
import secrets
import time
from contextvars import ContextVar

PBKDF2_ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 200
SESSION_COOKIE_NAME = "sv_session"
SESSION_SECONDS = 12 * 60 * 60
# 이 요청을 보낸 로그인 계정 (웹 API의 require_login이 채운다)
CURRENT_USER = ContextVar("current_user", default=None)


def load_secret_key():
    """세션 서명 키. 환경 변수 SECRET_KEY를 쓰고, 없으면 서버 시작 때 무작위로 만든다 (R-08)."""
    value = os.environ.get("SECRET_KEY", "").strip()
    return value.encode("utf-8") if value else secrets.token_bytes(32)


def password_problem(password):
    """비밀번호 규칙을 어기면 한글 안내 문구를, 맞으면 None을 돌려준다."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"비밀번호는 {MAX_PASSWORD_LENGTH}자 이하여야 합니다."
    return None


def hash_password(password, salt=None):
    """PBKDF2-HMAC-SHA256 해시. 저장 형식: pbkdf2_sha256$반복수$소금(hex)$해시(hex)."""
    salt = salt if salt is not None else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """입력한 비밀번호가 저장된 해시와 맞으면 True. 저장값이 없거나 형식이 다르면 False."""
    if not stored:
        return False
    try:
        scheme, iterations_text, salt_hex, digest_hex = stored.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _sign(payload, secret):
    return hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()


def make_session_token(username_key, secret, now=None):
    """계정 키와 만료 시각을 담고 서명한 세션 토큰을 만든다."""
    current = now if now is not None else time.time()
    expires = int(current + SESSION_SECONDS)
    payload = base64.urlsafe_b64encode(f"{username_key}\n{expires}".encode("utf-8")).decode("ascii")
    return f"{payload}.{_sign(payload, secret)}"


def read_session_token(token, secret, now=None):
    """세션 토큰을 검사하고 계정 키를 돌려준다. 서명이 틀리거나 만료됐으면 None."""
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    try:
        if not hmac.compare_digest(_sign(payload, secret), signature):
            return None
        username_key, expires_text = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8").split("\n")
        expires = int(expires_text)
    except (ValueError, UnicodeError):
        return None
    current = now if now is not None else time.time()
    if current >= expires:
        return None
    return username_key
