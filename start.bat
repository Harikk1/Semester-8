@echo off
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  SmartOps AI - Autonomous Incident Engine ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  [1/3] Installing AI Engine dependencies...
pip install -r smartops_engine\requirements.txt --quiet
echo.
echo  [2/3] Starting SmartOps AI Engine on port 9000...
echo        Dashboard: Open smartops-ai.html in browser
echo        API Docs:  http://localhost:9000/docs
echo        WS:        ws://localhost:9000/ws
echo.
echo  [3/3] Launch! Press Ctrl+C to stop.
echo.
cd smartops_engine
uvicorn main:app --host 0.0.0.0 --port 9000 --reload
