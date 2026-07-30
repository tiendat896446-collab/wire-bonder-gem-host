# Wire Bonder Monitor & Control Desktop Suite

An industrial, production-ready Desktop Application for monitoring and controlling a Wire Bonder machine. Designed with a sleek, high-fidelity dark-mode interface, featuring:
- Real-time Connection Status (Connected / Disconnected / Reconnecting).
- Live Telemetry Charts (Speed, Force, and Temperature plotted over time).
- Control Panel (Start/Stop operations, set recipe parameters, manual test alerts).
- Local SQLite database logging via asynchronous SQLAlchemy.
- Robust Serial / Modbus auto-reconnect state machine with high-fidelity Mock Simulation fallback.

---

## Technical Architecture

- **Backend**: Python 3.11+ using FastAPI, running uvicorn in a concurrent background daemon thread.
- **Frontend**: CustomTkinter for beautiful, responsive widgets without Electron's memory overhead.
- **Telemetry Charts**: Embedded Matplotlib utilizing the `FigureCanvasTkAgg` canvas wrapper.
- **Database**: SQLite database `wire_bonder_data.db` queried via async SQLAlchemy & `aiosqlite`.
- **Hardware Integration**: Runs a dedicated asynchronous `HardwareWorker` that automatically scans for active Modbus/Serial ports and falls back to a realistic mock simulation if no hardware is detected, preserving the retry loop.

---

## Setup & Running Directly via Python

### 1. Install Dependencies
Make sure you have Python 3.11+ installed. Install the listed production requirements:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Simply run the top-level launcher `main.py` script. This handles spinning up both the backend FastAPI server and the frontend CustomTkinter window in a single command:
```bash
python main.py
```
When closed, the launcher gracefully cleans up all background threads.

---

## Building the Standalone Executable

To compile and bundle the entire application (embedded server and UI) into a single-file executable (`.exe` on Windows, or generic executable on Linux/Mac) without external Python runtime dependencies:

```bash
python build_app.py
```

This uses **PyInstaller** to safely bundle CustomTkinter assets, FastAPI routers, SQLAlchemy dialects, and uvicorn binaries.
Once finished, you can find the self-contained executable in the `./dist/` directory:
- **Location**: `./dist/WireBonderControlSuite` (or `WireBonderControlSuite.exe` on Windows).

---

## Project Directory Structure

```text
├── backend/
│   ├── database.py       # Async SQLite SQLAlchemy session engine
│   ├── models.py         # DB models (Telemetry, Alarms, Recipes)
│   ├── hardware.py       # Modbus / PySerial auto-reconnect worker
│   └── main.py           # FastAPI Web Server (REST & WebSockets)
├── frontend/
│   ├── app.py            # Main GUI coordinator
│   └── components/       # Sleek CustomTkinter widgets
│       ├── connection.py # Status banner
│       ├── charts.py     # Live Matplotlib charts
│       ├── control.py    # Operations and recipes form
│       └── alarms.py     # Alarms logs and CSV exporter
├── .gitignore            # Version control exclusions
├── build_app.py          # PyInstaller bundle script
├── main.py               # Single dual-entrypoint launcher
├── requirements.txt      # Production dependencies
├── test_suite.py         # End-to-end integration test suite
└── README.md             # This document
```
