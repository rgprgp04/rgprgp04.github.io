@echo off
setlocal enabledelayedexpansion
chcp 936 >nul
cd /d "%~dp0"
echo 正在启动本地转发服务...
start "m3u8本地转发服务" /min cmd /c "node server.js > server.log 2>&1"
ping -n 3 127.0.0.1 >nul
curl.exe -s http://127.0.0.1:8787/health >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 服务未启动成功，可能原因如下，请检查：
    echo  1. 端口 8787 已被占用 - 关掉之前的服务或改 server.js 里的 PORT
    echo  2. Node.js 未安装或不在 PATH
    echo.
    echo ------ server.log 内容 ------
    type server.log 2>nul
    echo ------------------------------
    echo.
    pause
    goto end
)

:select_menu
echo.
echo 服务已启动，请选择要打开的页面：
echo  1 - 打开 m3u8解析.html (默认)
echo  2 - 打开 avdown-mobile.html
echo  3 - 打开 finance.html
set "sel="
set /p sel=请输入数字(1/2/3)，直接回车默认1: 

:: 如果直接回车 sel为空，默认1
if "!sel!"=="" set sel=1

if "!sel!"=="1" (
    start "" "%~dp0m3u8解析.html"
) else if "!sel!"=="2" (
    start "" "%~dp0avdown-mobile.html"
) else if "!sel!"=="3" (
    start "" "%~dp0finance.html"
) else (
    echo 输入无效！请重新选择。
    goto select_menu
)

echo.
echo 页面已打开。
echo 关闭服务：关掉任务栏最小化黑色窗口；
echo 或者执行：netstat -ano ^| findstr 8787 后 taskkill /PID 对应进程

:end
endlocal
