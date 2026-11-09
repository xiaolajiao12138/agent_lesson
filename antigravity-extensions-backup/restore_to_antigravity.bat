@echo off
chcp 65001 >nul
title 还原 Antigravity IDE 插件与配置到新电脑

echo ========================================================
echo        Antigravity IDE 完整环境一键克隆还原工具
echo ========================================================
echo.

set EXT_SRC=%~dp0extensions_offline
set CONF_SRC=%~dp0user_config_offline

set EXT_DST=%USERPROFILE%\.antigravity-ide\extensions
if not exist "%USERPROFILE%\.antigravity-ide" if exist "%USERPROFILE%\.antigravity" set EXT_DST=%USERPROFILE%\.antigravity\extensions

set CONF_DST=%APPDATA%\Antigravity IDE\User
if not exist "%APPDATA%\Antigravity IDE" if exist "%APPDATA%\Antigravity" set CONF_DST=%APPDATA%\Antigravity\User

if not exist "%EXT_SRC%" (
    echo [错误] 当前目录下未找到 extensions_offline 文件夹！
    echo 请确认是否已先在原电脑上运行了 backup_to_here.bat 提取环境。
    pause
    exit /b 1
)

echo [1/2] 正在还原 25 个插件到 %EXT_DST% ...
if not exist "%EXT_DST%" mkdir "%EXT_DST%"
xcopy "%EXT_SRC%" "%EXT_DST%\" /E /I /H /Y /Q >nul

echo [2/2] 正在还原用户设置（主题、快捷键、代码片段）到 %CONF_DST% ...
if not exist "%CONF_DST%" mkdir "%CONF_DST%"
if exist "%CONF_SRC%\settings.json" copy /y "%CONF_SRC%\settings.json" "%CONF_DST%\" >nul
if exist "%CONF_SRC%\keybindings.json" copy /y "%CONF_SRC%\keybindings.json" "%CONF_DST%\" >nul
if exist "%CONF_SRC%\snippets" xcopy "%CONF_SRC%\snippets" "%CONF_DST%\snippets\" /E /I /H /Y /Q >nul

echo.
echo ========================================================
echo [还原成功！] 
echo Antigravity IDE 的插件、主题、快捷键与设置已全部克隆完毕！
echo 启动或重启新电脑上的 Antigravity IDE 即可立即使用。
echo ========================================================
pause
