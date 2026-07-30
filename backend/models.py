from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from backend.database import Base

class TelemetryModel(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    temperature = Column(Float, nullable=False)
    bond_force = Column(Float, nullable=False)
    ultrasonic_power = Column(Float, nullable=False)
    speed = Column(Float, nullable=False)
    cycle_time = Column(Float, nullable=False)
    status = Column(String, nullable=False) # e.g., "IDLE", "RUNNING", "ALARM", "DISCONNECTED"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "temperature": self.temperature,
            "bond_force": self.bond_force,
            "ultrasonic_power": self.ultrasonic_power,
            "speed": self.speed,
            "cycle_time": self.cycle_time,
            "status": self.status
        }

class AlarmModel(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    code = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=False) # "INFO", "WARNING", "CRITICAL"
    status = Column(String, default="ACTIVE", nullable=False) # "ACTIVE", "RESOLVED"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "status": self.status
        }

class RecipeModel(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    bond_force = Column(Float, nullable=False)
    ultrasonic_power = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    bond_time = Column(Float, nullable=False) # in milliseconds

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bond_force": self.bond_force,
            "ultrasonic_power": self.ultrasonic_power,
            "temperature": self.temperature,
            "bond_time": self.bond_time
        }
