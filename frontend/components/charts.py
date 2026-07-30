import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from datetime import datetime

class TelemetryCharts(ctk.CTkFrame):
    """
    Component for rendering live charts using embedded Matplotlib.
    Maintains a history of parameters to draw speed, temperature, and bond force over time.
    """
    def __init__(self, master, max_history=30, **kwargs):
        super().__init__(master, **kwargs)
        self.max_history = max_history

        # Deques to store historical telemetry data
        self.timestamps = deque(maxlen=max_history)
        self.temperatures = deque(maxlen=max_history)
        self.forces = deque(maxlen=max_history)
        self.speeds = deque(maxlen=max_history)

        # Style configurations matching Dark Mode
        plt.style.use("dark_background")
        self.fig, (self.ax_temp, self.ax_force, self.ax_speed) = plt.subplots(3, 1, figsize=(6, 5), sharex=True)
        self.fig.patch.set_facecolor("#1D1E22") # Matches ctk frame dark bg

        # Subplot 1: Temperature
        self.ax_temp.set_facecolor("#1D1E22")
        self.ax_temp.set_ylabel("Temp (°C)", color="#FF8800")
        self.ax_temp.tick_params(colors="#CCCCCC", labelsize=8)
        self.ax_temp.grid(True, color="#333333", linestyle="--")
        self.line_temp, = self.ax_temp.plot([], [], color="#FF8800", linewidth=2, label="Temperature")

        # Subplot 2: Force
        self.ax_force.set_facecolor("#1D1E22")
        self.ax_force.set_ylabel("Force (g)", color="#00C851")
        self.ax_force.tick_params(colors="#CCCCCC", labelsize=8)
        self.ax_force.grid(True, color="#333333", linestyle="--")
        self.line_force, = self.ax_force.plot([], [], color="#00C851", linewidth=2, label="Force")

        # Subplot 3: Speed
        self.ax_speed.set_facecolor("#1D1E22")
        self.ax_speed.set_ylabel("Speed (BPH)", color="#33B5E5")
        self.ax_speed.tick_params(colors="#CCCCCC", labelsize=8)
        self.ax_speed.grid(True, color="#333333", linestyle="--")
        self.line_speed, = self.ax_speed.plot([], [], color="#33B5E5", linewidth=2, label="Speed")

        self.fig.tight_layout()

        # Canvas Embed
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def append_data(self, temp: float, force: float, speed: float):
        """
        Appends a new data point and schedules a redraw.
        """
        now = datetime.now().strftime("%H:%M:%S")
        self.timestamps.append(now)
        self.temperatures.append(temp)
        self.forces.append(force)
        self.speeds.append(speed)

        # Update lines data
        x = list(range(len(self.timestamps)))

        # Temp plot update
        self.line_temp.set_data(x, list(self.temperatures))
        self.ax_temp.set_xlim(0, max(self.max_history - 1, len(self.timestamps)))
        if self.temperatures:
            self.ax_temp.set_ylim(min(self.temperatures) - 5, max(self.temperatures) + 5)

        # Force plot update
        self.line_force.set_data(x, list(self.forces))
        if self.forces:
            self.ax_force.set_ylim(min(self.forces) - 5, max(self.forces) + 5)

        # Speed plot update
        self.line_speed.set_data(x, list(self.speeds))
        if self.speeds:
            self.ax_speed.set_ylim(min(self.speeds) - 50, max(self.speeds) + 50)

        # Draw update
        self.canvas.draw_idle()
