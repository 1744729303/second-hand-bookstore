@echo off
chcp 65001 >nul
echo ================================
echo 二手图书交易平台 - 快速启动
echo ================================
echo.
echo 正在启动应用...
echo 应用地址: http://localhost:5000
echo.
echo 测试账号:
echo   买家 - 用户名: buyer1, 密码: 123456
echo   卖家 - 用户名: seller1, 密码: 123456
echo.
echo 按 Ctrl+C 停止服务器
echo ================================
echo.
python app.py
pause
