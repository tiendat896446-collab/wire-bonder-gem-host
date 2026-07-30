import customtkinter as ctk

class ConnectionWidget(ctk.CTkFrame):
    """
    Component for rendering connection and machine statuses inside the sidebar.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Heading
        self.label_title = ctk.CTkLabel(self, text="MACHINE INTERFACE", font=ctk.CTkFont(size=14, weight="bold"))
        self.label_title.pack(pady=(10, 15), padx=10)

        # Connection Status
        self.conn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.conn_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_conn_title = ctk.CTkLabel(self.conn_frame, text="COM Link:", font=ctk.CTkFont(size=12))
        self.lbl_conn_title.pack(side="left")

        self.lbl_conn_val = ctk.CTkLabel(
            self.conn_frame,
            text="DISCONNECTED",
            text_color="#FF4C4C",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_conn_val.pack(side="right")

        # Driver Mode Indicator
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_mode_title = ctk.CTkLabel(self.mode_frame, text="Driver Mode:", font=ctk.CTkFont(size=12))
        self.lbl_mode_title.pack(side="left")

        self.lbl_mode_val = ctk.CTkLabel(
            self.mode_frame,
            text="HARDWARE",
            text_color="#9933CC",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_mode_val.pack(side="right")

        # Machine Active State
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=10, pady=(5, 15))

        self.lbl_status_title = ctk.CTkLabel(self.status_frame, text="State:", font=ctk.CTkFont(size=12))
        self.lbl_status_title.pack(side="left")

        self.lbl_status_val = ctk.CTkLabel(
            self.status_frame,
            text="IDLE",
            text_color="#E0E0E0",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_status_val.pack(side="right")

    def update_status(self, connected: bool, reconnecting: bool, mode: str, status: str):
        """
        Updates the status UI widgets dynamically.
        """
        # Connection status color
        if reconnecting:
            self.lbl_conn_val.configure(text="RECONNECTING", text_color="#FFBB33")
        elif connected:
            self.lbl_conn_val.configure(text="CONNECTED", text_color="#00C851")
        else:
            self.lbl_conn_val.configure(text="DISCONNECTED", text_color="#FF4C4C")

        # Driver Mode
        self.lbl_mode_val.configure(text=mode.upper(), text_color="#33B5E5" if mode == "Simulation" else "#9933CC")

        # State color
        if status == "RUNNING":
            self.lbl_status_val.configure(text="RUNNING", text_color="#00C851")
        elif status == "ALARM":
            self.lbl_status_val.configure(text="ALARM DETECTED", text_color="#FF4C4C")
        else:
            self.lbl_status_val.configure(text="IDLE", text_color="#E0E0E0")
