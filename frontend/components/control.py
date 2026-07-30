import customtkinter as ctk
import requests
import threading
from tkinter import messagebox

class ControlPanel(ctk.CTkFrame):
    """
    Component for managing:
    - Start/Stop operations
    - Mode selection (Hardware / Simulation)
    - Recipe upload parameters
    - Triggering physical/mock errors and resolutions
    """
    def __init__(self, master, backend_url="http://127.0.0.1:8000", **kwargs):
        super().__init__(master, **kwargs)
        self.backend_url = backend_url

        # Header Title
        self.title = ctk.CTkLabel(self, text="MACHINE CONTROL PANEL", font=ctk.CTkFont(size=14, weight="bold"))
        self.title.pack(pady=10, padx=10)

        # ---------------- OPERATION CONTROL BUTTONS ----------------
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ctk.CTkButton(
            self.btn_frame,
            text="START BONDING",
            fg_color="#00C851",
            hover_color="#007E33",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_start
        )
        self.btn_start.pack(fill="x", padx=10, pady=5)

        self.btn_stop = ctk.CTkButton(
            self.btn_frame,
            text="STOP OPERATIONS",
            fg_color="#FF4C4C",
            hover_color="#CC0000",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_stop
        )
        self.btn_stop.pack(fill="x", padx=10, pady=5)

        # ---------------- MODE & SERIAL CONFIGURATION ----------------
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(fill="x", padx=10, pady=5)

        # Sub-grid inside mode_frame for neat layout
        self.mode_frame.grid_columnconfigure(1, weight=1)

        # Mode Row
        ctk.CTkLabel(self.mode_frame, text="Active Driver Mode:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.mode_var = ctk.StringVar(value="Hardware")
        self.mode_dropdown = ctk.CTkOptionMenu(
            self.mode_frame,
            values=["Hardware", "Simulation"],
            variable=self.mode_var,
            width=120,
            command=self._on_mode_change
        )
        self.mode_dropdown.grid(row=0, column=1, sticky="e", padx=10, pady=5)

        # Port Row
        ctk.CTkLabel(self.mode_frame, text="COM Port:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.entry_port = ctk.CTkEntry(self.mode_frame, placeholder_text="COM1", width=120)
        self.entry_port.grid(row=1, column=1, sticky="e", padx=10, pady=3)
        self.entry_port.insert(0, "COM1")

        # Baudrate Row
        ctk.CTkLabel(self.mode_frame, text="Baudrate:", font=ctk.CTkFont(size=11)).grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.entry_baud = ctk.CTkEntry(self.mode_frame, placeholder_text="9600", width=120)
        self.entry_baud.grid(row=2, column=1, sticky="e", padx=10, pady=3)
        self.entry_baud.insert(0, "9600")

        # Apply Serial Config Button
        self.btn_serial_config = ctk.CTkButton(
            self.mode_frame,
            text="APPLY PORT CONFIG",
            fg_color="#33B5E5",
            hover_color="#0099CC",
            height=24,
            command=self._on_apply_serial_config
        )
        self.btn_serial_config.grid(row=3, column=0, columnspan=2, sticky="we", padx=10, pady=(5, 10))

        # ---------------- PARAMETERS / RECIPE FORM ----------------
        self.recipe_frame = ctk.CTkFrame(self)
        self.recipe_frame.pack(fill="x", padx=10, pady=10)

        self.recipe_title = ctk.CTkLabel(self.recipe_frame, text="Recipe Settings", font=ctk.CTkFont(size=12, weight="bold"))
        self.recipe_title.grid(row=0, column=0, columnspan=2, pady=5)

        # Name
        ctk.CTkLabel(self.recipe_frame, text="Name:").grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.entry_name = ctk.CTkEntry(self.recipe_frame, placeholder_text="e.g., QFN-LeadFree")
        self.entry_name.grid(row=1, column=1, padx=10, pady=3, sticky="we")
        self.entry_name.insert(0, "Gold-Wire-01")

        # Bond Force
        ctk.CTkLabel(self.recipe_frame, text="Force (g):").grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.entry_force = ctk.CTkEntry(self.recipe_frame, placeholder_text="40 - 70")
        self.entry_force.grid(row=2, column=1, padx=10, pady=3, sticky="we")
        self.entry_force.insert(0, "50.0")

        # Ultrasonic Power
        ctk.CTkLabel(self.recipe_frame, text="Power (mW):").grid(row=3, column=0, sticky="w", padx=10, pady=3)
        self.entry_power = ctk.CTkEntry(self.recipe_frame, placeholder_text="50 - 80")
        self.entry_power.grid(row=3, column=1, padx=10, pady=3, sticky="we")
        self.entry_power.insert(0, "65.0")

        # Temperature
        ctk.CTkLabel(self.recipe_frame, text="Temp (°C):").grid(row=4, column=0, sticky="w", padx=10, pady=3)
        self.entry_temp = ctk.CTkEntry(self.recipe_frame, placeholder_text="180 - 220")
        self.entry_temp.grid(row=4, column=1, padx=10, pady=3, sticky="we")
        self.entry_temp.insert(0, "200.0")

        # Bond Time
        ctk.CTkLabel(self.recipe_frame, text="Time (ms):").grid(row=5, column=0, sticky="w", padx=10, pady=3)
        self.entry_time = ctk.CTkEntry(self.recipe_frame, placeholder_text="10 - 30")
        self.entry_time.grid(row=5, column=1, padx=10, pady=3, sticky="we")
        self.entry_time.insert(0, "15.0")

        # Upload Button
        self.btn_recipe = ctk.CTkButton(
            self.recipe_frame,
            text="APPLY RECIPE",
            fg_color="#33B5E5",
            hover_color="#0099CC",
            text_color="white",
            command=self._on_apply_recipe
        )
        self.btn_recipe.grid(row=6, column=0, columnspan=2, pady=10, padx=10, sticky="we")

        # Configure columns
        self.recipe_frame.grid_columnconfigure(1, weight=1)

        # ---------------- TEST ALARM ACTIONS ----------------
        self.alarm_ctrl_frame = ctk.CTkFrame(self)
        self.alarm_ctrl_frame.pack(fill="x", padx=10, pady=5)

        self.btn_trigger_alarm = ctk.CTkButton(
            self.alarm_ctrl_frame,
            text="TRIGGER MOCK ALARM",
            fg_color="#FF8800",
            hover_color="#E65100",
            text_color="white",
            command=self._on_trigger_alarm
        )
        self.btn_trigger_alarm.pack(fill="x", padx=10, pady=5)

        self.btn_resolve_alarm = ctk.CTkButton(
            self.alarm_ctrl_frame,
            text="RESOLVE ACTIVE ALARMS",
            fg_color="#00C851",
            hover_color="#007E33",
            text_color="white",
            command=self._on_resolve_alarm
        )
        self.btn_resolve_alarm.pack(fill="x", padx=10, pady=5)

    def _api_call(self, method: str, endpoint: str, json_data: dict = None):
        """Helper to run API calls in a background thread avoiding UI freeze."""
        def run():
            try:
                url = f"{self.backend_url}{endpoint}"
                if method == "POST":
                    r = requests.post(url, json=json_data, timeout=3.0)
                else:
                    r = requests.get(url, timeout=3.0)

                if r.status_code != 200:
                    print(f"[API ERROR] Status: {r.status_code}, Body: {r.text}")
            except Exception as e:
                print(f"[API EXCEPTION] {e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_start(self):
        print("[UI] Clicking START BONDING")
        self._api_call("POST", "/api/control/start")

    def _on_stop(self):
        print("[UI] Clicking STOP OPERATIONS")
        self._api_call("POST", "/api/control/stop")

    def _on_trigger_alarm(self):
        print("[UI] Triggering Mock Alarm")
        self._api_call("POST", "/api/control/test")

    def _on_resolve_alarm(self):
        print("[UI] Resolving Mock Alarm")
        self._api_call("POST", "/api/control/resolve")

    def _on_mode_change(self, mode):
        print(f"[UI] Changing Driver Mode manually to {mode}")
        self._api_call("POST", f"/api/control/mode?mode={mode}")

    def _on_apply_serial_config(self):
        port = self.entry_port.get().strip()
        baud_str = self.entry_baud.get().strip()

        if not port:
            messagebox.showerror("Validation Error", "COM Port cannot be empty.")
            return

        try:
            baudrate = int(baud_str)
        except ValueError:
            messagebox.showerror("Validation Error", "Baudrate must be an integer.")
            return

        if baudrate <= 0:
            messagebox.showerror("Validation Error", "Baudrate must be positive.")
            return

        print(f"[UI] Applying dynamic Serial Config: {port} at {baudrate} bps")
        self._api_call("POST", f"/api/control/config_serial?port={port}&baudrate={baudrate}")

    def _on_apply_recipe(self):
        # 1. Gather & Validate parameters
        name = self.entry_name.get().strip()
        force_str = self.entry_force.get().strip()
        power_str = self.entry_power.get().strip()
        temp_str = self.entry_temp.get().strip()
        time_str = self.entry_time.get().strip()

        if not name:
            messagebox.showerror("Validation Error", "Recipe Name cannot be empty.")
            return

        try:
            force = float(force_str)
            power = float(power_str)
            temp = float(temp_str)
            b_time = float(time_str)
        except ValueError:
            messagebox.showerror("Validation Error", "Parameters must be numeric.")
            return

        # Simple threshold check
        if force <= 0 or power <= 0 or temp <= 0 or b_time <= 0:
            messagebox.showerror("Validation Error", "All parameters must be strictly greater than zero.")
            return

        print(f"[UI] Applying Recipe parameters: {name} Force={force}, Power={power}, Temp={temp}")
        payload = {
            "name": name,
            "bond_force": force,
            "ultrasonic_power": power,
            "temperature": temp,
            "bond_time": b_time
        }
        self._api_call("POST", "/api/recipes", payload)
