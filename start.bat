@echo off
echo ================================
echo 法律智能问答系统启动脚本
echo ================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装后端依赖...
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [3/3] 检查前端环境...
cd ..\frontend
where npm >nul 2>nul
if errorlevel 1 (
    echo 警告: 未找到npm，请先安装Node.js
) else (
    echo 安装前端依赖...
    npm install
)

echo.
echo ================================
echo 环境准备完成！
echo ================================
echo.
echo 启动方式：
echo   后端: cd backend ^&^& python main.py
echo   前端: cd frontend ^&^& npm run dev
echo.
echo 请确保已启动Milvus服务：
echo   docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest
echo.
pause
