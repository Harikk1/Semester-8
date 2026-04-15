#!/usr/bin/env python3
"""
SmartOps AI – Quick Start Script
Run this to install deps and launch the AI engine locally.
"""
import subprocess, sys, os

def run(cmd, **kw):
    print(f"\n{'─'*60}\n▶ {cmd}\n{'─'*60}")
    subprocess.run(cmd, shell=True, check=True, **kw)

eng_dir = os.path.join(os.path.dirname(__file__), "smartops_engine")

print("╔══════════════════════════════════════════╗")
print("║  SmartOps AI - Autonomous Incident Engine ║")
print("╚══════════════════════════════════════════╝\n")

# Install deps
run(f'pip install -r "{os.path.join(eng_dir, "requirements.txt")}" --quiet')

# Launch engine
print("\n🚀 Starting SmartOps AI Engine on http://localhost:9000")
print("📊 Open smartops-ai.html in your browser")
print("🔗 WS: ws://localhost:9000/ws\n")

os.chdir(eng_dir)
run(f"{sys.executable} -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload")
