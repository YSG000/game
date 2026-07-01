@echo off
chcp 65001 >nul
title 오늘의 기억 - 순위 서버
cd /d "%~dp0"
echo ============================================================
echo    오늘의 기억 - 부서 순위표 서버
echo ============================================================
echo.
echo [1/3] 8000 포트에 남아있는 예전 서버 종료...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
  echo    - 예전 서버 종료 ^(PID %%a^)
  taskkill /F /PID %%a >nul 2>nul
)
timeout /t 1 /nobreak >nul
echo    완료.
echo.
echo [2/3] 브라우저 열기 ^(잠시 후 게임이 뜹니다^)...
start "" http://localhost:8000
echo.
echo [3/3] 서버 시작 - 이 창을 닫으면 서버가 꺼집니다.
echo    같은 와이파이의 다른 기기는  http://이PC의IP:8000  으로 접속하세요.
echo.
where python >nul 2>nul
if %errorlevel%==0 (
  python leaderboard_server.py
) else (
  py leaderboard_server.py
)
echo.
echo 서버가 종료되었거나, 이 PC에서 파이썬을 찾지 못했습니다.
pause
