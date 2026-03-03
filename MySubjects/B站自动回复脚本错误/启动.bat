@echo off
chcp 65001 >nul
title B站自动回复工具
echo ==========================================
echo     B站自动回复工具
echo     Python 3.12.3
echo ==========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.12.3
    echo 下载地址: https://www.python.org/downloads/release/python-3123/
    echo.
    pause
    exit /b 1
)

:: 显示Python版本
echo [信息] Python版本:
python --version
echo.

:: 检查requests库
echo [信息] 检查依赖库...
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [警告] 未安装requests库，正在安装...
    pip install requests
    if errorlevel 1 (
        echo [错误] 安装requests失败，请手动执行: pip install requests
        pause
        exit /b 1
    )
    echo [成功] requests安装完成
) else (
    echo [成功] 依赖库检查通过
)
echo.

:: 启动程序
echo [信息] 正在启动B站自动回复工具...
echo ==========================================
echo.
python bilibili_auto_reply.py

:: 如果程序异常退出
echo.
echo ==========================================
echo [警告] 程序已退出
pause
