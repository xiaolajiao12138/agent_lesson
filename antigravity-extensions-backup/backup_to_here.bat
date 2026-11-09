@echo off
chcp 65001 >nul
title 备份 Antigravity IDE 插件与完整配置

echo ========================================================
echo       Antigravity IDE 完整环境一键备份工具
echo   （包含：25个插件 + settings.json + 快捷键 + 代码片段）
echo ========================================================
echo.

set EXT_SRC=%USERPROFILE%\.antigravity-ide\extensions
if not exist "%EXT_SRC%" set EXT_SRC=%USERPROFILE%\.antigravity\extensions

set CONF_SRC=%APPDATA%\Antigravity IDE\User
if not exist "%CONF_SRC%" set CONF_SRC=%APPDATA%\Antigravity\User

set EXT_DST=%~dp0extensions_offline
set CONF_DST=%~dp0user_config_offline

if not exist "%EXT_SRC%" (
    echo [错误] 未在当前电脑找到 Antigravity 插件目录: %EXT_SRC%
    pause
    exit /b 1
)

echo [1/2] 正在备份插件目录到 %EXT_DST% ...
xcopy "%EXT_SRC%" "%EXT_DST%\" /E /I /H /Y /Q >nul

echo [2/2] 正在备份用户设置（settings.json, keybindings, snippets）到 %CONF_DST% ...
if not exist "%CONF_DST%" mkdir "%CONF_DST%"
if exist "%CONF_SRC%\settings.json" copy /y "%CONF_SRC%\settings.json" "%CONF_DST%\" >nul
if exist "%CONF_SRC%\keybindings.json" copy /y "%CONF_SRC%\keybindings.json" "%CONF_DST%\" >nul
if exist "%CONF_SRC%\snippets" xcopy "%CONF_SRC%\snippets" "%CONF_DST%\snippets\" /E /I /H /Y /Q >nul

echo.
echo ========================================================
echo [备份成功！] 
echo 插件与全部配置已完整导出到当前文件夹：
echo   - 插件库: extensions_offline
echo   - 配置项: user_config_offline (含设置、快捷键、代码片段)
echo.
echo 请将整个 antigravity-extensions-backup 文件夹复制到新电脑，
echo 然后在新电脑运行 restore_to_antigravity.bat 即可一键完全克隆！
echo ========================================================
pause
