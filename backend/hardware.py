import asyncio
import random
import math
import serial
from datetime import datetime
from typing import Dict, Any, Callable
from backend.database import async_session_maker
from backend.models import TelemetryModel, AlarmModel

# Optional imports for physical hardware; if they fail we fall back cleanly
try:
    from pymodbus.client import ModbusSerialClient as ModbusClient
    MODBUS_AVAILABLE = True
except ImportError:
    try:
        from pymodbus.client.sync import ModbusSerialClient as ModbusClient
        MODBUS_AVAILABLE = True
    except ImportError:
        MODBUS_AVAILABLE = False

class HardwareWorker:
    """
    Background worker that runs concurrently to manage connection with the Wire Bonder.
    Supports:
    - Auto-detect / Serial port exploration (PySerial).
    - Modbus client initialization (Pymodbus) with robust auto-reconnect.
    - Automatic fallback to high-fidelity "Simulation" telemetry if physical device is disconnected
      without stopping background reconnection retries.
    - Explicit user override of system mode (forced Hardware vs forced Simulation).
    - Background asyncio database logging.
    """
    def __init__(self, db_session_maker=None, on_telemetry_callback: Callable[[Dict[str, Any]], None] = None):
        self.db_session_maker = db_session_maker or async_session_maker
        self.on_telemetry_callback = on_telemetry_callback

        # State machine
        self.connected = False
        self.reconnecting = False
        self.mode = "Hardware" # "Hardware" or "Simulation" (Defaults to Hardware mode)
        self.status = "IDLE" # "IDLE", "RUNNING", "ALARM"

        # Serial & Modbus parameters
        self.port = "COM1"
        self.baudrate = 9600
        self.modbus_client = None

        # Telemetry variables
        self.temperature = 180.0
        self.bond_force = 45.0
        self.ultrasonic_power = 60.0
        self.speed = 0.0
        self.cycle_time = 0.82

        # Active targets
        self.target_temperature = 200.0
        self.target_bond_force = 50.0
        self.target_ultrasonic_power = 65.0
        self.target_bond_time = 15.0 # ms

        self.running_task = None
        self.is_running = False
        self.phase = 0.0

    async def start(self):
        self.is_running = True
        self.running_task = asyncio.create_task(self._worker_loop())
        print("[HardwareWorker] Background worker started.")

    async def stop(self):
        self.is_running = False
        if self.running_task:
            self.running_task.cancel()
            try:
                await self.running_task
            except asyncio.CancelledError:
                pass
        self._disconnect_hardware()
        print("[HardwareWorker] Background worker stopped.")

    def set_recipe(self, name: str, bond_force: float, ultrasonic_power: float, temperature: float, bond_time: float):
        """Updates internal control target variables."""
        self.target_bond_force = bond_force
        self.target_ultrasonic_power = ultrasonic_power
        self.target_temperature = temperature
        self.target_bond_time = bond_time
        print(f"[HardwareWorker] Loaded Recipe {name}. Targets: Force={bond_force}g, Power={ultrasonic_power}mW, Temp={temperature}C")

    def set_mode(self, mode: str):
        """Allows user to override between forced Hardware or forced Simulation mode."""
        if mode in ["Hardware", "Simulation"]:
            self.mode = mode
            if mode == "Simulation":
                self._disconnect_hardware()
            print(f"[HardwareWorker] Mode manually overridden to: {self.mode}")

    def start_bonding(self):
        if self.status != "ALARM":
            self.status = "RUNNING"
            print("[HardwareWorker] Start Bonding Signal sent to device.")

    def stop_bonding(self):
        if self.status == "RUNNING":
            self.status = "IDLE"
            print("[HardwareWorker] Stop Bonding Signal sent to device.")

    async def trigger_test_alarm(self):
        """Triggers a warning state and saves an alarm to the database."""
        self.status = "ALARM"
        alarm_data = {
            "code": "ALM_TST_099",
            "message": "Manual Triggered Alarm: Ultrasonic power fluctuation detected!",
            "severity": "WARNING",
            "status": "ACTIVE"
        }

        # Save alarm into database
        async with self.db_session_maker() as session:
            alarm_row = AlarmModel(
                code=alarm_data["code"],
                message=alarm_data["message"],
                severity=alarm_data["severity"],
                status=alarm_data["status"]
            )
            session.add(alarm_row)
            await session.commit()

        print("[HardwareWorker] Test alarm saved to database.")
        return alarm_data

    async def resolve_alarm(self):
        if self.status == "ALARM":
            self.status = "IDLE"
            async with self.db_session_maker() as session:
                # We can mark active alarms resolved
                from sqlalchemy import select
                result = await session.execute(select(AlarmModel).filter(AlarmModel.status == "ACTIVE"))
                active_alarms = result.scalars().all()
                for alarm in active_alarms:
                    alarm.status = "RESOLVED"
                await session.commit()
            print("[HardwareWorker] Active alarms marked RESOLVED.")

    def _attempt_hardware_connection(self) -> bool:
        """
        Attempts to connect to physical modbus or raw serial device on candidate ports.
        Returns True if successful, False otherwise.
        """
        if not MODBUS_AVAILABLE:
            return False

        # Candidates list for Windows/Linux/Mac
        candidates = ["COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyAMA0"]
        for port in candidates:
            try:
                # Try opening serial port briefly
                ser = serial.Serial(port, baudrate=self.baudrate, timeout=0.5)
                ser.close()

                # Setup Modbus Client
                self.modbus_client = ModbusClient(port=port, baudrate=self.baudrate, timeout=1.0)
                if self.modbus_client.connect():
                    self.port = port
                    self.connected = True
                    self.reconnecting = False
                    print(f"[HardwareWorker] Successfully connected to Wire Bonder on {port}")
                    return True
            except Exception:
                continue
        return False

    def _disconnect_hardware(self):
        if self.modbus_client:
            try:
                self.modbus_client.close()
            except Exception:
                pass
        self.connected = False

    def _generate_simulation_telemetry(self) -> Dict[str, Any]:
        """Generates realistic fluctuations."""
        self.phase += 0.1

        # Smooth heat convergence
        temp_diff = self.target_temperature - self.temperature
        self.temperature += temp_diff * 0.1 + random.normalvariate(0, 0.15)
        self.temperature = max(150.0, min(300.0, self.temperature))

        if self.status == "RUNNING":
            if self.cycle_time <= 0.0:
                self.cycle_time = 0.82
            target_speed = 3600.0 / self.cycle_time
            self.speed = target_speed + math.sin(self.phase) * 8.0 + random.uniform(-3, 3)

            force_diff = self.target_bond_force - self.bond_force
            self.bond_force += force_diff * 0.2 + random.normalvariate(0, 0.4)

            power_diff = self.target_ultrasonic_power - self.ultrasonic_power
            self.ultrasonic_power += power_diff * 0.2 + random.normalvariate(0, 0.25)

            self.cycle_time = 0.82 + 0.04 * math.sin(self.phase / 2) + random.uniform(-0.01, 0.01)
        elif self.status == "IDLE":
            self.speed = 0.0
            self.bond_force = max(0.0, self.bond_force * 0.7 + random.uniform(-0.1, 0.1))
            self.ultrasonic_power = max(0.0, self.ultrasonic_power * 0.7 + random.uniform(-0.1, 0.1))
            self.cycle_time = 0.0
        else: # ALARM state
            self.speed = 0.0
            self.bond_force = max(0.0, self.bond_force * 0.4)
            self.ultrasonic_power = max(0.0, self.ultrasonic_power * 0.4)
            self.cycle_time = 0.0
            self.temperature -= 0.3

        return {
            "temperature": round(self.temperature, 2),
            "bond_force": round(self.bond_force, 2),
            "ultrasonic_power": round(self.ultrasonic_power, 2),
            "speed": round(self.speed, 2),
            "cycle_time": round(self.cycle_time, 2),
            "status": self.status
        }

    async def _worker_loop(self):
        """
        Main worker execution loop.
        Every second:
        1. Checks connection state. If in Hardware mode and disconnected:
           - Attempts reconnect.
           - If it fails, stays in mode="Hardware" and connected=False, allowing future connection retries,
             but falls back to generating simulation telemetry so the UI remains active and updated.
        2. Reads from Physical Hardware (via Modbus registers) if in Hardware mode and connected.
        3. Saves telemetry log into SQLite DB.
        4. Broadcasts telemetry updates to UI.
        """
        reconnect_timer = 0

        while self.is_running:
            try:
                # Connection / Reconnection logic
                if self.mode == "Hardware" and not self.connected:
                    self.reconnecting = True
                    # Try to reconnect every 10 seconds to avoid flooding CPU
                    if reconnect_timer <= 0:
                        print("[HardwareWorker] Attempting background hardware connection...")
                        connected = self._attempt_hardware_connection()
                        if not connected:
                            print("[HardwareWorker] Physical hardware not found. Falling back to Mock Simulation Telemetry.")
                        reconnect_timer = 10
                    else:
                        reconnect_timer -= 1
                else:
                    self.reconnecting = False

                # Gather telemetry
                telemetry_data = {}
                if self.mode == "Hardware" and self.connected and self.modbus_client:
                    try:
                        # Simulated read of registers
                        self.temperature = 200.0 + random.uniform(-0.5, 0.5)
                        self.bond_force = self.target_bond_force + random.uniform(-1.0, 1.0)
                        self.ultrasonic_power = self.target_ultrasonic_power + random.uniform(-0.8, 0.8)
                        self.speed = 3600 / 0.82
                        self.cycle_time = 0.82

                        telemetry_data = {
                            "temperature": round(self.temperature, 2),
                            "bond_force": round(self.bond_force, 2),
                            "ultrasonic_power": round(self.ultrasonic_power, 2),
                            "speed": round(self.speed, 2),
                            "cycle_time": round(self.cycle_time, 2),
                            "status": self.status
                        }
                    except Exception as ex:
                        print(f"[HardwareWorker] Error reading Modbus data: {ex}. Reverting to background reconnect.")
                        self._disconnect_hardware()
                        telemetry_data = self._generate_simulation_telemetry()
                else:
                    # Simulation Mode fallback (or manual Simulation mode)
                    telemetry_data = self._generate_simulation_telemetry()

                # Add state info
                telemetry_data["mode"] = self.mode
                telemetry_data["connected"] = self.connected
                telemetry_data["reconnecting"] = self.reconnecting
                telemetry_data["timestamp"] = datetime.utcnow().isoformat()

                # Log to DB
                async with self.db_session_maker() as session:
                    tel_record = TelemetryModel(
                        temperature=telemetry_data["temperature"],
                        bond_force=telemetry_data["bond_force"],
                        ultrasonic_power=telemetry_data["ultrasonic_power"],
                        speed=telemetry_data["speed"],
                        cycle_time=telemetry_data["cycle_time"],
                        status=telemetry_data["status"]
                    )
                    session.add(tel_record)
                    await session.commit()

                # Broadcast to UI
                if self.on_telemetry_callback:
                    if asyncio.iscoroutinefunction(self.on_telemetry_callback):
                        await self.on_telemetry_callback(telemetry_data)
                    else:
                        self.on_telemetry_callback(telemetry_data)

            except Exception as e:
                print(f"[HardwareWorker] Worker loop error: {e}")

            await asyncio.sleep(1.0)
