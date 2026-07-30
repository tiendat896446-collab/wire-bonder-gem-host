import os
import asyncio
import csv
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, desc

from backend.database import init_db, async_session_maker
from backend.models import TelemetryModel, AlarmModel, RecipeModel
from backend.hardware import HardwareWorker

# Define Pydantic models for request bodies
class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    bond_force: float = Field(..., gt=0)
    ultrasonic_power: float = Field(..., gt=0)
    temperature: float = Field(..., gt=0)
    bond_time: float = Field(..., gt=0)

# Create FastAPI app
app = FastAPI(title="Wire Bonder Dashboard Backend")

# We will initialize this on startup
hardware_worker: Optional[HardwareWorker] = None
connected_websockets: List[WebSocket] = []

async def broadcast_telemetry(data: Dict[str, Any]):
    """Broadcasts telemetry data to all active WebSocket clients."""
    if not connected_websockets:
        return

    # Clean/serialize any datetime objects
    serialized_data = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            serialized_data[k] = v.isoformat()
        else:
            serialized_data[k] = v

    # Broadcast to all connected clients
    for websocket in list(connected_websockets):
        try:
            await websocket.send_json(serialized_data)
        except Exception:
            connected_websockets.remove(websocket)

@app.on_event("startup")
async def startup_event():
    global hardware_worker
    await init_db()

    # Start the hardware background task
    hardware_worker = HardwareWorker(
        db_session_maker=async_session_maker,
        on_telemetry_callback=broadcast_telemetry
    )
    await hardware_worker.start()

@app.on_event("shutdown")
async def shutdown_event():
    global hardware_worker
    if hardware_worker:
        await hardware_worker.stop()

# --- REST API Endpoints ---

@app.post("/api/recipes")
async def create_recipe(recipe: RecipeCreate):
    async with async_session_maker() as session:
        # Check if recipe exists
        stmt = select(RecipeModel).filter(RecipeModel.name == recipe.name)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            # Update existing
            existing.bond_force = recipe.bond_force
            existing.ultrasonic_power = recipe.ultrasonic_power
            existing.temperature = recipe.temperature
            existing.bond_time = recipe.bond_time
            await session.commit()

            # Update worker Targets if active
            if hardware_worker:
                hardware_worker.set_recipe(
                    existing.name, existing.bond_force, existing.ultrasonic_power, existing.temperature, existing.bond_time
                )
            return {"status": "updated", "recipe": existing.to_dict()}

        db_recipe = RecipeModel(
            name=recipe.name,
            bond_force=recipe.bond_force,
            ultrasonic_power=recipe.ultrasonic_power,
            temperature=recipe.temperature,
            bond_time=recipe.bond_time
        )
        session.add(db_recipe)
        await session.commit()
        await session.refresh(db_recipe)

        # Load immediately to the hardware worker
        if hardware_worker:
            hardware_worker.set_recipe(
                db_recipe.name, db_recipe.bond_force, db_recipe.ultrasonic_power, db_recipe.temperature, db_recipe.bond_time
            )

        return {"status": "created", "recipe": db_recipe.to_dict()}

@app.get("/api/recipes")
async def get_recipes():
    async with async_session_maker() as session:
        result = await session.execute(select(RecipeModel))
        recipes = result.scalars().all()
        return [r.to_dict() for r in recipes]

@app.post("/api/control/start")
async def start_bonding():
    if hardware_worker:
        hardware_worker.start_bonding()
        return {"status": "success", "message": "Bonding operation started."}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.post("/api/control/stop")
async def stop_bonding():
    if hardware_worker:
        hardware_worker.stop_bonding()
        return {"status": "success", "message": "Bonding operation stopped."}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.post("/api/control/test")
async def trigger_test_alarm():
    if hardware_worker:
        alarm_data = await hardware_worker.trigger_test_alarm()
        return {"status": "success", "alarm": alarm_data}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.post("/api/control/resolve")
async def resolve_alarms():
    if hardware_worker:
        await hardware_worker.resolve_alarm()
        return {"status": "success", "message": "Alarms resolved successfully."}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.post("/api/control/mode")
async def set_driver_mode(mode: str):
    if hardware_worker:
        hardware_worker.set_mode(mode)
        return {"status": "success", "mode": mode}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.post("/api/control/config_serial")
async def config_serial(port: str, baudrate: int):
    if hardware_worker:
        hardware_worker.config_serial(port, baudrate)
        return {"status": "success", "port": port, "baudrate": baudrate}
    raise HTTPException(status_code=503, detail="Hardware service unavailable.")

@app.get("/api/alarms")
async def get_alarms(severity: Optional[str] = None):
    async with async_session_maker() as session:
        stmt = select(AlarmModel).order_by(desc(AlarmModel.timestamp))
        if severity and severity != "ALL":
            stmt = stmt.filter(AlarmModel.severity == severity.upper())
        result = await session.execute(stmt)
        alarms = result.scalars().all()
        return [a.to_dict() for a in alarms]

@app.get("/api/alarms/export")
async def export_alarms_csv():
    async with async_session_maker() as session:
        result = await session.execute(select(AlarmModel).order_by(desc(AlarmModel.timestamp)))
        alarms = result.scalars().all()

        # Write CSV output
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Code", "Message", "Severity", "Status"])
        for a in alarms:
            writer.writerow([a.id, a.timestamp.isoformat(), a.code, a.message, a.severity, a.status])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=alarm_history.csv"}
        )

# --- WebSocket Telemetry Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    print(f"[WebSocket] Client connected. Active connections: {len(connected_websockets)}")
    try:
        while True:
            # Keep connection alive, listen for messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
        print(f"[WebSocket] Client disconnected. Active connections: {len(connected_websockets)}")
    except Exception as e:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
        print(f"[WebSocket] Client disconnected with error: {e}")
