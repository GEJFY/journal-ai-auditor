@echo off
chcp 65001 >nul
title JAIA - Journal entry AI Analyzer

echo ========================================
echo   JAIA - Journal entry AI Analyzer
echo   ワンクリック起動
echo ========================================
echo.

:: プロジェクトルートを取得
set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"

:: バックエンド起動
echo [1/2] バックエンドを起動しています...
start "JAIA Backend" cmd /k "cd /d "%BACKEND_DIR%" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload"

:: バックエンド起動を待機
echo   バックエンド起動を待機中（5秒）...
timeout /t 5 /nobreak >nul

:: フロントエンド起動
echo [2/2] フロントエンドを起動しています...
start "JAIA Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ========================================
echo   起動完了！
echo ========================================
echo.
echo   バックエンド API:  http://localhost:8090
echo   Swagger UI:        http://localhost:8090/docs
echo   フロントエンド:    http://localhost:5290
echo.
echo   ※ 初回はブラウザで http://localhost:5290 を開いてください
echo   ※ 終了するには各ウィンドウを閉じてください
echo.
pause
