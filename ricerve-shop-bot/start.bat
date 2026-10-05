@echo off
chcp 65001 >nul
title Shop Bot
cd /d "%~dp0"

echo =======================================
echo   ОЧИСТКА КЭША
echo =======================================
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc >nul 2>&1

echo =======================================
echo   УСТАНОВКА ЗАВИСИМОСТЕЙ
echo =======================================
pip install -r requirements.txt --quiet

echo.
echo =======================================
echo   ЗАПУСК МАГАЗИНА
echo =======================================
echo.

python bot.py

echo.
echo Бот остановлен. Нажмите любую клавишу для выхода.
pause
