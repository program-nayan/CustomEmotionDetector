#!/usr/bin/env python
"""
Start the Serenity Wellness Assistant API server.
Run from project root: python run_server.py
"""
import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print("🚀 Launching Serenity Wellness Assistant Server...")
print("📝 Logs will be saved in the './logs/' directory.")
subprocess.run([sys.executable,"-m","uvicorn","api.app:app","--host","0.0.0.0","--port","8000","--reload"])
