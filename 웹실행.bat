@echo off
rem 2026-11-18 - 클로드 스마트 보카 - 웹 버전을 더블클릭으로 실행하는 배치 파일
rem 파일 위치: 웹실행.bat (프로젝트 루트)
rem 사용: 이 파일을 더블클릭하면 웹 서버가 켜지고 브라우저가 열립니다. 창을 닫으면 서버가 꺼집니다.
rem 점검만 할 때: 명령 프롬프트에서 웹실행.bat check
chcp 65001 >nul
title 스마트 보카 - 웹 실행
cd /d "%~dp0"

set "PY="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.11"
if defined PY goto check_packages
python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto check_packages
echo Python 3.11을 찾을 수 없습니다.
echo Python 3.11을 설치한 뒤 다시 실행하세요.
pause
exit /b 1

:check_packages
%PY% -c "import fastapi, uvicorn, httpx" >nul 2>&1
if not errorlevel 1 goto ready
echo.
echo 웹 실행에 필요한 패키지가 설치되어 있지 않습니다.
echo   필요한 패키지: fastapi, uvicorn, httpx (requirements.txt 기준)
echo   설치 명령: %PY% -m pip install -r requirements.txt
echo.
if /i "%~1"=="check" goto check_missing
set "ANSWER="
set /p "ANSWER=지금 설치할까요? 인터넷 연결이 필요합니다. (Y/N): "
if /i not "%ANSWER%"=="Y" goto install_declined
echo.
echo 패키지를 설치합니다. 잠시 기다려 주세요...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto install_failed
%PY% -c "import fastapi, uvicorn, httpx" >nul 2>&1
if errorlevel 1 goto install_failed
echo.
echo 패키지 설치가 끝났습니다.
goto ready

:install_declined
echo.
echo 설치하지 않아 웹 서버를 시작할 수 없습니다.
echo 나중에 다시 실행하면 설치를 물어봅니다.
pause
exit /b 1

:install_failed
echo.
echo 패키지 설치에 실패했습니다. 인터넷 연결을 확인한 뒤 다시 실행하세요.
pause
exit /b 1

:check_missing
echo 점검 결과: 패키지가 없습니다. (서버는 실행하지 않았습니다.)
exit /b 1

:ready
if /i "%~1"=="check" goto check_only
echo 스마트 보카 웹 서버를 시작합니다.
echo 이 창을 닫으면 서버가 종료됩니다.
echo.
%PY% web\run.py
if errorlevel 1 (
  echo.
  echo 서버 실행 중 오류가 발생했습니다. 위 메시지를 확인하세요.
  pause
)
exit /b 0

:check_only
echo 점검 완료: Python과 패키지가 준비되어 있습니다. (서버는 실행하지 않았습니다.)
exit /b 0
