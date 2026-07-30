import os
import sys
import time
import subprocess
import threading
import socket
import uvicorn
from frontend.app import WireBonderApp

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

from backend.main import app as fastapi_app

def run_backend():
    """Runs the backend FastAPI server."""
    print("[Launcher] Starting backend FastAPI service on port 8000...")
    # Pass the app object directly so PyInstaller can perform static import tracing on the entire backend package.
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

def main():
    print("[Launcher] Initializing Wire Bonder Control Suite...")

    # 1. Start backend in a background daemon thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Wait for backend to spin up and bind port
    for _ in range(10):
        if is_port_in_use(8000):
            print("[Launcher] Backend service detected and running successfully.")
            break
        time.sleep(0.5)
    else:
        print("[Launcher] Warning: Backend connection check timed out. Continuing to load UI...")

    # 2. Start the CustomTkinter GUI main loop
    print("[Launcher] Launching GUI...")
    app = WireBonderApp(backend_url="http://127.0.0.1:8000", ws_url="ws://127.0.0.1:8000/ws")

    try:
        app.mainloop()
    finally:
        print("[Launcher] GUI closed. Initiating clean exit sequence.")

if __name__ == "__main__":
    main()
