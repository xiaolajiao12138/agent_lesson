@echo off
chcp 65001 >nul
title Antigravity IDE 插件一键批量安装工具

echo ========================================================
echo        Antigravity IDE 插件一键批量安装脚本
echo ========================================================
echo.

set CLI_CMD=

:: 1. 检测命令行工具
where antigravity >nul 2>nul
if %errorlevel% equ 0 (
    set CLI_CMD=antigravity
    goto :START_INSTALL
)

where code >nul 2>nul
if %errorlevel% equ 0 (
    set CLI_CMD=code
    goto :START_INSTALL
)

:: 如果没有在系统 PATH 中找到，提示用户
echo [提示] 系统环境变量中未直接找到 'antigravity' 或 'code' 命令。
echo 请确保：
echo   1. 在新电脑上已安装好 Antigravity IDE 或 VS Code；
echo   2. 或者直接在 Antigravity 编辑器内打开终端（按 Ctrl + `），然后运行此脚本；
echo   3. 或者使用更推荐的【离线物理拷贝】方案（复制 .antigravity 文件夹）。
echo.
pause
exit /b 1

:START_INSTALL
echo [检测成功] 将使用命令行工具: %CLI_CMD% 进行批量安装
echo.

set EXT_FILE=%~dp0extensions_clean.txt

if not exist "%EXT_FILE%" (
    echo [错误] 找不到插件列表文件: %EXT_FILE%
    pause
    exit /b 1
)

set /a count=0
for /f "usebackq tokens=*" %%i in ("%EXT_FILE%") do (
    set /a count+=1
    echo ----------------------------------------------------
    echo [正在安装 %%count%%/25] 插件: %%i
    echo ----------------------------------------------------
    %CLI_CMD% --install-extension "%%i" --force
)

echo.
echo ========================================================
echo [完成] 所有 Antigravity IDE 插件安装完毕！
echo 请重启或刷新 Antigravity IDE 编辑器使插件完全生效。
echo ========================================================
pause

