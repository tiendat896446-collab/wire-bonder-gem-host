import asyncio
import unittest
from sqlalchemy import select
from backend.database import init_db, async_session_maker
from backend.models import TelemetryModel, AlarmModel, RecipeModel
from backend.hardware import HardwareWorker

class TestWireBonderSystem(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Initialize SQLite database
        await init_db()

    async def test_full_data_path_and_state_transitions(self):
        print("\n[TEST] Beginning End-to-End System Integration Test...")

        # 1. Start worker
        telemetry_received = []
        def on_telemetry(data):
            telemetry_received.append(data)

        worker = HardwareWorker(db_session_maker=async_session_maker, on_telemetry_callback=on_telemetry)
        await worker.start()

        # 2. Allow worker to generate a few telemetry points
        await asyncio.sleep(2.5)

        # Ensure telemetry points were generated and captured by callbacks
        self.assertGreaterEqual(len(telemetry_received), 2)
        last_tel = telemetry_received[-1]

        # Verify simulated values conform to physical boundaries
        self.assertTrue(150.0 <= last_tel["temperature"] <= 300.0)
        self.assertEqual(last_tel["status"], "IDLE")
        self.assertEqual(last_tel["mode"], "Hardware") # Defaults to Hardware

        print("[TEST] Verified initial simulation parameters & IDLE state.")

        # 3. Simulate Setting a Recipe
        worker.set_recipe(
            name="TestRecipe",
            bond_force=60.0,
            ultrasonic_power=75.0,
            temperature=220.0,
            bond_time=20.0
        )

        # 4. Start Bonding operations
        worker.start_bonding()
        await asyncio.sleep(2.5)

        last_tel = telemetry_received[-1]
        self.assertEqual(last_tel["status"], "RUNNING")
        # Ensure values fluctuate and trend towards targets under active running
        self.assertGreater(last_tel["speed"], 0)
        self.assertGreater(last_tel["bond_force"], 0)

        print("[TEST] Verified transition to RUNNING state & recipe loading.")

        # 5. Trigger Manual Alarm
        alarm_resp = await worker.trigger_test_alarm()
        self.assertEqual(alarm_resp["code"], "ALM_TST_099")
        self.assertEqual(alarm_resp["severity"], "WARNING")

        await asyncio.sleep(1.5)
        last_tel = telemetry_received[-1]
        self.assertEqual(last_tel["status"], "ALARM")
        self.assertEqual(last_tel["speed"], 0.0) # Speed drops to zero immediately in ALARM

        print("[TEST] Verified transition to ALARM state and immediate speed halting.")

        # 6. Verify Alarm recorded in SQLite
        async with async_session_maker() as session:
            stmt = select(AlarmModel).filter(AlarmModel.code == "ALM_TST_099")
            db_alarm = (await session.execute(stmt)).scalar_one_or_none()
            self.assertIsNotNone(db_alarm)
            self.assertEqual(db_alarm.severity, "WARNING")
            self.assertEqual(db_alarm.status, "ACTIVE")

        print("[TEST] Verified alarm record insertion in SQLite.")

        # 7. Resolve Alarm
        await worker.resolve_alarm()
        await asyncio.sleep(1.5)

        last_tel = telemetry_received[-1]
        self.assertEqual(last_tel["status"], "IDLE") # Reset back to IDLE state

        # Verify DB status is now RESOLVED
        async with async_session_maker() as session:
            stmt = select(AlarmModel).filter(AlarmModel.code == "ALM_TST_099")
            db_alarm = (await session.execute(stmt)).scalar_one_or_none()
            self.assertEqual(db_alarm.status, "RESOLVED")

        print("[TEST] Verified alarm resolution and return to IDLE.")

        # Clean up
        await worker.stop()

if __name__ == "__main__":
    unittest.main()
