import sys
import os
import asyncio
import json
import threading
import customtkinter as ctk
from datetime import datetime

# Add root folder to sys.path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frontend.components.connection import ConnectionWidget
from frontend.components.charts import TelemetryCharts
from frontend.components.control import ControlPanel
from frontend.components.alarms import AlarmsTable

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WireBonderApp(ctk.CTk):
    """
    Main Desktop App window. Coordinates background WebSocket telemetry
    updates and connects individual UI components together.
    """
    def __init__(self, backend_url="http://127.0.0.1:8000", ws_url="ws://127.0.0.1:8000/ws"):
        super().__init__()

        self.backend_url = backend_url
        self.ws_url = ws_url

        # Window settings
        self.title("WIRE BONDER MONITOR & CONTROL DASHBOARD")
        self.geometry("1280x768")
        self.configure(fg_color="#141518") # Elegant sleek base background

        # ---------------- GRID CONFIGURATION ----------------
        self.grid_columnconfigure(0, weight=1) # Sidebar
        self.grid_columnconfigure(1, weight=3) # Middle: Charts
        self.grid_columnconfigure(2, weight=2) # Right: Control panel
        self.grid_rowconfigure(0, weight=1)

        # ---------------- SIDEBAR AREA ----------------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1D1E22")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Title Header
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="NEXUS BONDER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#33B5E5"
        )
        self.logo_label.pack(pady=(20, 5))

        self.sublogo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Control Suite v4.0",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.sublogo_label.pack(pady=(0, 20))

        # Divider
        self.div1 = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#2D2F36")
        self.div1.pack(fill="x", padx=15, pady=5)

        # Connection status component
        self.connection_widget = ConnectionWidget(self.sidebar_frame, fg_color="transparent")
        self.connection_widget.pack(fill="x", padx=10, pady=10)

        # Divider
        self.div2 = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#2D2F36")
        self.div2.pack(fill="x", padx=15, pady=5)

        # Statistics / Summary Info
        self.summary_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(self.summary_frame, text="OPERATIONAL STATS", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 10))

        self.lbl_total_bonds = ctk.CTkLabel(self.summary_frame, text="Total Bonds: 0", font=ctk.CTkFont(size=12))
        self.lbl_total_bonds.pack(anchor="w", pady=2)

        self.lbl_cycle_time = ctk.CTkLabel(self.summary_frame, text="Cycle Time: 0.00s", font=ctk.CTkFont(size=12))
        self.lbl_cycle_time.pack(anchor="w", pady=2)

        # ---------------- MIDDLE CONTENT: CHARTS & LOGS ----------------
        self.middle_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.middle_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.middle_frame.grid_columnconfigure(0, weight=1)
        self.middle_frame.grid_rowconfigure(0, weight=2) # Charts takes more space
        self.middle_frame.grid_rowconfigure(1, weight=1) # Alarm table below

        # Embed Charts Component
        self.charts_widget = TelemetryCharts(self.middle_frame, fg_color="#1D1E22")
        self.charts_widget.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # Embed Alarms Component
        self.alarms_widget = AlarmsTable(self.middle_frame, backend_url=self.backend_url, fg_color="#1D1E22")
        self.alarms_widget.grid(row=1, column=0, sticky="nsew")

        # ---------------- RIGHT CONTENT: CONTROL PANEL ----------------
        self.control_widget = ControlPanel(self, backend_url=self.backend_url, fg_color="#1D1E22")
        self.control_widget.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)

        # ---------------- BACKGROUND WEBSOCKET LISTENER ----------------
        self.total_bonds_counter = 0
        self.ws_connected = False
        self.ws_reconnecting = False

        # Start websocket polling/listen thread
        self.is_running = True
        self.thread = threading.Thread(target=self._websocket_listen_loop, daemon=True)
        self.thread.start()

    def _websocket_listen_loop(self):
        """
        Runs inside a daemon thread. Keeps an open WebSocket connection with FastAPI,
        reading real-time data packets and feeding them back to Tkinter via .after() methods.
        """
        import websockets

        async def listen():
            while self.is_running:
                try:
                    self.ws_reconnecting = True
                    self.update_connection_ui()

                    async with websockets.connect(self.ws_url) as ws:
                        self.ws_connected = True
                        self.ws_reconnecting = False
                        self.update_connection_ui()
                        print("[WS Client] Successfully connected to FastAPI telemetry stream.")

                        while self.is_running:
                            msg = await ws.recv()
                            payload = json.loads(msg)
                            self.after(0, self._process_telemetry_payload, payload)

                except Exception as e:
                    self.ws_connected = False
                    self.update_connection_ui()
                    print(f"[WS Client] Disconnected/Error: {e}. Retrying in 2 seconds...")
                    await asyncio.sleep(2.0)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(listen())

    def update_connection_ui(self):
        """Thread-safe connection update."""
        self.after(0, lambda: self.connection_widget.update_status(
            connected=self.ws_connected,
            reconnecting=self.ws_reconnecting,
            mode="Hardware",
            status="IDLE"
        ))

    def _process_telemetry_payload(self, payload: dict):
        """
        Handles parsed JSON packet received over WS.
        Updates charts, counters, state indicators, and tables dynamically.
        """
        temp = payload.get("temperature", 180.0)
        force = payload.get("bond_force", 0.0)
        power = payload.get("ultrasonic_power", 0.0)
        speed = payload.get("speed", 0.0)
        cycle_time = payload.get("cycle_time", 0.0)
        status = payload.get("status", "IDLE")
        mode = payload.get("mode", "Hardware")
        connected = payload.get("connected", False)
        reconnecting = payload.get("reconnecting", False)

        # Update Connection Widget Status
        self.connection_widget.update_status(
            connected=connected,
            reconnecting=reconnecting,
            mode=mode,
            status=status
        )

        # Update Control Widget Mode dropdown indicator if changed externally
        self.control_widget.mode_var.set(mode)

        # If status is RUNNING, let's accumulate some simulated product count
        if status == "RUNNING":
            self.total_bonds_counter += 1

        self.lbl_total_bonds.configure(text=f"Total Bonds: {self.total_bonds_counter}")
        self.lbl_cycle_time.configure(text=f"Cycle Time: {cycle_time:.2f}s")

        # Refresh Alarm logs if machine triggered a new state
        if status == "ALARM":
            self.alarms_widget.fetch_alarms()

        # Update live graphing lines
        self.charts_widget.append_data(temp=temp, force=force, speed=speed)

    def destroy(self):
        self.is_running = False
        super().destroy()

if __name__ == "__main__":
    app = WireBonderApp()
    app.mainloop()
