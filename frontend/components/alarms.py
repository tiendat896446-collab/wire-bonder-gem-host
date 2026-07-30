import customtkinter as ctk
import requests
import threading
import os
from datetime import datetime
from tkinter import filedialog, messagebox

class AlarmsTable(ctk.CTkFrame):
    """
    Component for viewing historical alarms.
    Includes:
    - Active filter dropdown.
    - Refresh action.
    - Export alarm list to CSV via a native save file dialog.
    """
    def __init__(self, master, backend_url="http://127.0.0.1:8000", **kwargs):
        super().__init__(master, **kwargs)
        self.backend_url = backend_url

        # Header Title and Actions Frame
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=10, pady=5)

        self.title = ctk.CTkLabel(self.top_frame, text="ALARM & EVENT LOG", font=ctk.CTkFont(size=14, weight="bold"))
        self.title.pack(side="left", padx=5)

        # Export Button
        self.btn_export = ctk.CTkButton(
            self.top_frame,
            text="EXPORT CSV",
            fg_color="#33B5E5",
            hover_color="#0099CC",
            text_color="white",
            width=80,
            height=26,
            command=self._on_export
        )
        self.btn_export.pack(side="right", padx=5)

        # Refresh Button
        self.btn_refresh = ctk.CTkButton(
            self.top_frame,
            text="REFRESH",
            fg_color="#4B515D",
            hover_color="#3F729B",
            text_color="white",
            width=80,
            height=26,
            command=self.fetch_alarms
        )
        self.btn_refresh.pack(side="right", padx=5)

        # Filter Option
        self.filter_var = ctk.StringVar(value="ALL")
        self.filter_dropdown = ctk.CTkOptionMenu(
            self.top_frame,
            values=["ALL", "INFO", "WARNING", "CRITICAL"],
            variable=self.filter_var,
            width=100,
            height=26,
            command=lambda _: self.fetch_alarms()
        )
        self.filter_dropdown.pack(side="right", padx=5)

        # Scrollable table container
        self.table_container = ctk.CTkScrollableFrame(self, label_text="Timestamp | Code | Severity | Description | Status")
        self.table_container._label.configure(font=ctk.CTkFont(size=11, weight="bold"))
        self.table_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Initial pull
        self.fetch_alarms()

    def fetch_alarms(self):
        """Fetches filtered alarms asynchronously and updates grid rows."""
        severity = self.filter_var.get()

        def run():
            try:
                url = f"{self.backend_url}/api/alarms"
                if severity != "ALL":
                    url += f"?severity={severity}"

                r = requests.get(url, timeout=3.0)
                if r.status_code == 200:
                    alarms = r.json()
                    self.update_grid(alarms)
            except Exception as e:
                print(f"[UI ALARMS] Error fetching: {e}")

        threading.Thread(target=run, daemon=True).start()

    def update_grid(self, alarms):
        """Refreshes individual rows inside scrollable panel."""
        # Clean existing children in the table container
        for widget in self.table_container.winfo_children():
            widget.destroy()

        if not alarms:
            # Place empty status placeholder
            lbl = ctk.CTkLabel(self.table_container, text="No alarms found matching criteria.", text_color="#888888")
            lbl.pack(pady=20, fill="x")
            return

        for idx, a in enumerate(alarms):
            row_frame = ctk.CTkFrame(self.table_container, fg_color="#2D2F36" if idx % 2 == 0 else "#25272C")
            row_frame.pack(fill="x", pady=2, padx=2)

            # Columns layout
            ts_str = a.get("timestamp", "")
            if ts_str:
                try:
                    ts_str = datetime.fromisoformat(ts_str).strftime("%H:%M:%S")
                except ValueError:
                    pass

            code = a.get("code", "N/A")
            severity = a.get("severity", "INFO")
            msg = a.get("message", "")
            status = a.get("status", "ACTIVE")

            # Set colors per severity
            sev_color = "#FF8800" if severity == "WARNING" else "#FF4C4C" if severity == "CRITICAL" else "#33B5E5"

            # Render row widgets
            lbl_ts = ctk.CTkLabel(row_frame, text=ts_str, width=80, anchor="w", font=ctk.CTkFont(size=11))
            lbl_ts.pack(side="left", padx=5)

            lbl_code = ctk.CTkLabel(row_frame, text=code, width=100, anchor="w", font=ctk.CTkFont(size=11, weight="bold"))
            lbl_code.pack(side="left", padx=5)

            lbl_sev = ctk.CTkLabel(row_frame, text=severity, width=80, anchor="w", text_color=sev_color, font=ctk.CTkFont(size=11, weight="bold"))
            lbl_sev.pack(side="left", padx=5)

            lbl_msg = ctk.CTkLabel(row_frame, text=msg, anchor="w", font=ctk.CTkFont(size=11))
            lbl_msg.pack(side="left", fill="x", expand=True, padx=5)

            status_color = "#FF4C4C" if status == "ACTIVE" else "#00C851"
            lbl_status = ctk.CTkLabel(row_frame, text=status, width=70, anchor="e", text_color=status_color, font=ctk.CTkFont(size=11, weight="bold"))
            lbl_status.pack(side="right", padx=5)

    def _on_export(self):
        """Downloads the exported CSV file and saves to disk using file chooser."""
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Alarm Log to CSV",
            initialfile="alarm_history.csv"
        )
        if not save_path:
            return

        def run():
            try:
                url = f"{self.backend_url}/api/alarms/export"
                r = requests.get(url, timeout=5.0)
                if r.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    messagebox.showinfo("Export Success", f"Alarms successfully exported to:\n{save_path}")
                else:
                    messagebox.showerror("Export Failed", "Error exporting data from server.")
            except Exception as e:
                messagebox.showerror("Export Exception", f"Exception during export: {e}")

        threading.Thread(target=run, daemon=True).start()
