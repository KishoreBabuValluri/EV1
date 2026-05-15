"""
ChargeNexus OCPP 1.6 Charger Simulator
========================================
Simulates a real DC fast charger connecting to the ChargeNexus OCPP server.
Use this to test the full integration without real hardware.

Usage:
    python ocpp/simulator.py                        # simulate charger CN-HYD-001
    python ocpp/simulator.py --charger-id CN-HYD-002 --port 9000
    python ocpp/simulator.py --scenario full        # full session lifecycle
    python ocpp/simulator.py --scenario fault       # simulate a fault
    python ocpp/simulator.py --scenario heartbeat   # just keep-alive loop

Scenarios:
    boot        — BootNotification + StatusNotification (Available)
    heartbeat   — boot + continuous heartbeats
    full        — boot + start charge + meter values + stop charge (complete session)
    fault       — boot + StatusNotification(Faulted) + recovery
    rapid       — compressed full session (2 second meter intervals)
"""

import sys
import pathlib
# Ensure backend/ is on sys.path so the ocpp package is importable
_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import asyncio
import json
import logging
import random
import uuid
import argparse
from datetime import datetime

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIM %(name)s] %(levelname)s  %(message)s",
)

RFID_TAG = "driver@demo.com"    # matches demo driver email used as id_tag


class ChargerSimulator:
    """Simulates a single OCPP 1.6 Charge Point."""

    def __init__(
        self,
        charger_id: str,
        server_url: str,
        connector_count: int = 2,
        power_kw: float = 60,
    ):
        self.charger_id     = charger_id
        self.server_url     = server_url.rstrip("/")
        self.connector_count = connector_count
        self.power_kw       = power_kw
        self.ws             = None
        self.log            = logging.getLogger(charger_id)

        # State per connector (1-indexed)
        self.connector_status: dict[int, str] = {
            i: "Available" for i in range(1, connector_count + 1)
        }
        self.active_transactions: dict[int, int] = {}   # connector_id → transaction_id
        self.meter_values: dict[int, float] = {
            i: 0.0 for i in range(1, connector_count + 1)
        }   # cumulative Wh per connector

        # Pending responses: msg_id → asyncio.Future
        self._pending: dict[str, asyncio.Future] = {}
        self._receiver_task: asyncio.Task = None

    # ── connection ─────────────────────────────────────────────────────────────

    async def connect(self):
        url = f"{self.server_url}/ocpp/{self.charger_id}"
        self.log.info("Connecting to %s ...", url)
        # websockets 13.x: use websockets.asyncio.client.connect
        from websockets.asyncio.client import connect as ws_connect
        self.ws = await ws_connect(
            url,
            subprotocols=["ocpp1.6"],
            ping_interval=None,   # we manage our own heartbeat
        )
        self.log.info("Connected.")
        # Start background receiver
        self._receiver_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self):
        if self._receiver_task:
            self._receiver_task.cancel()
        if self.ws:
            await self.ws.close()
        self.log.info("Disconnected.")

    # ── low-level send/receive ─────────────────────────────────────────────────

    async def _send_call(self, action: str, payload: dict) -> dict:
        msg_id = str(uuid.uuid4())
        frame  = json.dumps([2, msg_id, action, payload])
        loop   = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[msg_id] = future
        await self.ws.send(frame)
        self.log.debug("→ %s %s", action, payload)
        try:
            result = await asyncio.wait_for(future, timeout=30)
            self.log.debug("← CALLRESULT %s", result)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise TimeoutError(f"No response to {action}")

    async def _receive_loop(self):
        """Background task — processes incoming CS→CP commands."""
        try:
            async for raw in self.ws:
                await self._handle_incoming(raw)
        except Exception:
            self.log.info("Server closed connection.")

    async def _handle_incoming(self, raw: str):
        try:
            msg = json.loads(raw)
        except Exception:
            return

        msg_type = msg[0]
        msg_id   = msg[1]

        if msg_type == 3:   # CALLRESULT
            payload = msg[2] if len(msg) > 2 else {}
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                future.set_result(payload)

        elif msg_type == 4:   # CALLERROR
            error = msg[2] if len(msg) > 2 else "Unknown"
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                future.set_exception(RuntimeError(f"CALLERROR: {error}"))

        elif msg_type == 2:   # CALL from CS (remote command)
            action  = msg[2]
            payload = msg[3] if len(msg) > 3 else {}
            self.log.info("← CS command: %s %s", action, payload)
            await self._handle_cs_command(msg_id, action, payload)

    async def _send_result(self, msg_id: str, payload: dict):
        frame = json.dumps([3, msg_id, payload])
        await self.ws.send(frame)

    async def _handle_cs_command(self, msg_id: str, action: str, payload: dict):
        """Handle commands sent from the Central System."""
        if action == "RemoteStartTransaction":
            connector_id = payload.get("connectorId", 1)
            id_tag       = payload.get("idTag", RFID_TAG)
            await self._send_result(msg_id, {"status": "Accepted"})
            # Simulate the charging sequence asynchronously
            asyncio.create_task(self._simulate_charge_sequence(connector_id, id_tag))

        elif action == "RemoteStopTransaction":
            transaction_id = payload.get("transactionId")
            # Find connector for this transaction
            connector_id = next(
                (c for c, t in self.active_transactions.items() if t == transaction_id), None
            )
            if connector_id:
                await self._send_result(msg_id, {"status": "Accepted"})
                asyncio.create_task(self._simulate_stop(connector_id, "Remote"))
            else:
                await self._send_result(msg_id, {"status": "Rejected"})

        elif action == "ChangeAvailability":
            connector_id   = payload.get("connectorId", 0)
            avail_type     = payload.get("type", "Operative")
            await self._send_result(msg_id, {"status": "Accepted"})
            new_status = "Available" if avail_type == "Operative" else "Unavailable"
            connectors = [connector_id] if connector_id > 0 else list(self.connector_status.keys())
            for c in connectors:
                asyncio.create_task(self._send_status(c, new_status))

        elif action == "Reset":
            reset_type = payload.get("type", "Soft")
            await self._send_result(msg_id, {"status": "Accepted"})
            self.log.info("Reset requested (%s) — simulating reboot...", reset_type)
            asyncio.create_task(self._simulate_reboot())

        elif action == "GetConfiguration":
            keys = payload.get("key", [])
            config = {
                "HeartbeatInterval": "60",
                "MeterValueSampleInterval": "30",
                "NumberOfConnectors": str(self.connector_count),
                "ChargePointModel": "CN-SIM-DC60",
                "ChargePointVendor": "ChargeNexus",
                "MaxChargingProfilesInstalled": "10",
                "SupportedFeatureProfiles": "Core,FirmwareManagement,LocalAuthListManagement",
            }
            result_keys = []
            for k in (keys or config.keys()):
                if k in config:
                    result_keys.append({"key": k, "readonly": False, "value": config[k]})
                else:
                    result_keys.append({"key": k, "readonly": False})
            await self._send_result(msg_id, {"configurationKey": result_keys, "unknownKey": []})

        elif action == "ChangeConfiguration":
            await self._send_result(msg_id, {"status": "Accepted"})

        elif action == "UnlockConnector":
            await self._send_result(msg_id, {"status": "Unlocked"})

        elif action == "ClearCache":
            await self._send_result(msg_id, {"status": "Accepted"})

        elif action == "TriggerMessage":
            requested = payload.get("requestedMessage", "Heartbeat")
            await self._send_result(msg_id, {"status": "Accepted"})
            if requested == "Heartbeat":
                asyncio.create_task(self._heartbeat_once())
            elif requested == "StatusNotification":
                connector_id = payload.get("connectorId", 0)
                connectors = [connector_id] if connector_id > 0 else list(self.connector_status.keys())
                for c in connectors:
                    asyncio.create_task(self._send_status(c, self.connector_status[c]))
        else:
            self.log.warning("Unknown CS command: %s", action)
            frame = json.dumps([4, msg_id, "NotImplemented", f"{action} not implemented", {}])
            await self.ws.send(frame)

    # ── OCPP action helpers ───────────────────────────────────────────────────

    async def boot(self):
        result = await self._send_call("BootNotification", {
            "chargePointVendor": "ChargeNexus",
            "chargePointModel": "CN-SIM-DC60",
            "chargePointSerialNumber": f"SN-{self.charger_id}",
            "firmwareVersion": "1.4.2",
            "iccid": "89914503012345678901",
            "imsi": "404030123456789",
        })
        status = result.get("status")
        interval = result.get("interval", 60)
        self.log.info("Boot → status=%s heartbeat_interval=%ds", status, interval)
        return status, interval

    async def _send_status(self, connector_id: int, status: str,
                            error_code: str = "NoError", info: str = ""):
        self.connector_status[connector_id] = status
        await self._send_call("StatusNotification", {
            "connectorId": connector_id,
            "errorCode": error_code,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "info": info,
        })
        self.log.info("Status connector=%d → %s", connector_id, status)

    async def _heartbeat_once(self):
        result = await self._send_call("Heartbeat", {})
        self.log.debug("Heartbeat ack: %s", result.get("currentTime"))

    async def _send_meter_values(self, connector_id: int, transaction_id: int, wh: float):
        await self._send_call("MeterValues", {
            "connectorId": connector_id,
            "transactionId": transaction_id,
            "meterValue": [{
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sampledValue": [
                    {
                        "value": str(int(wh)),
                        "context": "Sample.Periodic",
                        "format": "Raw",
                        "measurand": "Energy.Active.Import.Register",
                        "unit": "Wh",
                    },
                    {
                        "value": str(round(self.power_kw * 1000, 0)),
                        "context": "Sample.Periodic",
                        "format": "Raw",
                        "measurand": "Power.Active.Import",
                        "unit": "W",
                    },
                    {
                        "value": str(round(random.uniform(380, 420), 1)),
                        "context": "Sample.Periodic",
                        "measurand": "Voltage",
                        "unit": "V",
                    },
                    {
                        "value": str(round(self.power_kw * 1000 / 400, 1)),
                        "context": "Sample.Periodic",
                        "measurand": "Current.Import",
                        "unit": "A",
                    },
                    {
                        "value": str(round(random.uniform(25, 45), 1)),
                        "context": "Sample.Periodic",
                        "measurand": "Temperature",
                        "unit": "Celsius",
                    },
                ],
            }],
        })

    async def _simulate_charge_sequence(self, connector_id: int = 1,
                                         id_tag: str = RFID_TAG,
                                         duration_seconds: int = 120,
                                         meter_interval_seconds: int = 30):
        """Full charge session: Preparing → Charging → MeterValues → StopTransaction → Available."""
        self.log.info("Starting charge sequence on connector %d for %ds", connector_id, duration_seconds)

        # 1. Preparing
        await self._send_status(connector_id, "Preparing")
        await asyncio.sleep(2)

        # 2. StartTransaction
        meter_start = int(self.meter_values.get(connector_id, 0))
        result = await self._send_call("StartTransaction", {
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": meter_start,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        txn_id = result.get("transactionId", -1)
        if txn_id < 0:
            self.log.error("StartTransaction rejected")
            await self._send_status(connector_id, "Available")
            return

        self.active_transactions[connector_id] = txn_id
        self.log.info("Transaction started: id=%d", txn_id)

        # 3. Charging status
        await self._send_status(connector_id, "Charging")

        # 4. Meter values loop
        elapsed = 0
        energy_wh = 0.0
        while elapsed < duration_seconds and connector_id in self.active_transactions:
            await asyncio.sleep(meter_interval_seconds)
            elapsed += meter_interval_seconds
            # Simulate energy delivery (power × time, with slight variance)
            delivered_wh = self.power_kw * 1000 * meter_interval_seconds / 3600 * random.uniform(0.9, 1.0)
            energy_wh += delivered_wh
            cumulative_wh = meter_start + energy_wh
            self.meter_values[connector_id] = cumulative_wh
            await self._send_meter_values(connector_id, txn_id, cumulative_wh)
            self.log.info("Meter: connector=%d energy=%.1fWh cumulative=%.1fWh",
                          connector_id, energy_wh, cumulative_wh)

        if connector_id in self.active_transactions:
            await self._simulate_stop(connector_id, "Local")

    async def _simulate_stop(self, connector_id: int, reason: str = "Local"):
        txn_id = self.active_transactions.pop(connector_id, None)
        if txn_id is None:
            return

        # 5. Finishing status
        await self._send_status(connector_id, "Finishing")
        await asyncio.sleep(1)

        # 6. StopTransaction
        meter_stop = int(self.meter_values.get(connector_id, 0))
        await self._send_call("StopTransaction", {
            "transactionId": txn_id,
            "meterStop": meter_stop,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
            "idTag": RFID_TAG,
        })
        self.log.info("Transaction stopped: id=%d meterStop=%dWh reason=%s", txn_id, meter_stop, reason)

        # 7. Available
        await asyncio.sleep(1)
        await self._send_status(connector_id, "Available")

    async def _simulate_reboot(self):
        """Simulate a soft/hard reset."""
        await asyncio.sleep(3)
        self.log.info("Rebooting...")
        # Send status Unavailable for all connectors
        for cid in self.connector_status:
            await self._send_status(cid, "Unavailable")
        await asyncio.sleep(2)
        # Re-boot
        status, _ = await self.boot()
        if status == "Accepted":
            for cid in self.connector_status:
                await self._send_status(cid, "Available")

    # ── scenarios ─────────────────────────────────────────────────────────────

    async def run_scenario(self, scenario: str):
        await self.connect()

        if scenario == "boot":
            await self.boot()
            await self._send_status(0, "Available")   # whole box
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            await asyncio.sleep(5)

        elif scenario == "heartbeat":
            status, interval = await self.boot()
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            self.log.info("Heartbeat loop every %ds. Ctrl+C to stop.", interval)
            while True:
                await asyncio.sleep(interval)
                await self._heartbeat_once()

        elif scenario == "full":
            status, _ = await self.boot()
            if status != "Accepted":
                self.log.error("Boot rejected — check charger_id is registered in ChargeNexus")
                return
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            await asyncio.sleep(2)
            # Simulate a 2-minute charge session on connector 1
            await self._simulate_charge_sequence(
                connector_id=1,
                duration_seconds=120,
                meter_interval_seconds=30,
            )
            self.log.info("Full scenario complete.")
            await asyncio.sleep(3)

        elif scenario == "rapid":
            # Same as full but compressed to seconds for quick testing
            status, _ = await self.boot()
            if status != "Accepted":
                self.log.error("Boot rejected")
                return
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            await asyncio.sleep(1)
            await self._simulate_charge_sequence(
                connector_id=1,
                duration_seconds=10,
                meter_interval_seconds=2,
            )
            self.log.info("Rapid scenario complete.")

        elif scenario == "fault":
            await self.boot()
            await self._send_status(0, "Available")
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            await asyncio.sleep(2)
            # Fault on connector 1
            self.log.info("Simulating fault on connector 1...")
            await self._send_status(1, "Faulted",
                                    error_code="HighTemperature",
                                    info="Thermal protection triggered")
            await asyncio.sleep(10)
            # Recovery
            self.log.info("Simulating fault recovery...")
            await self._send_status(1, "Available", info="Thermal OK")

        elif scenario == "multi":
            # Two connectors charging simultaneously
            status, _ = await self.boot()
            if status != "Accepted":
                return
            for cid in range(1, self.connector_count + 1):
                await self._send_status(cid, "Available")
            await asyncio.sleep(1)
            await asyncio.gather(
                self._simulate_charge_sequence(1, duration_seconds=60, meter_interval_seconds=15),
                self._simulate_charge_sequence(2, duration_seconds=45, meter_interval_seconds=15),
            )

        else:
            self.log.error("Unknown scenario: %s", scenario)

        await self.disconnect()


# ── CLI entrypoint ────────────────────────────────────────────────────────────

async def cli_main():
    parser = argparse.ArgumentParser(description="ChargeNexus OCPP 1.6 Charger Simulator")
    parser.add_argument("--charger-id", default="CN-HYD-001",
                        help="Charger ID (must be registered in ChargeNexus DB)")
    parser.add_argument("--host",       default="localhost",
                        help="OCPP server host")
    parser.add_argument("--port",       default=9000, type=int,
                        help="OCPP server port")
    parser.add_argument("--scenario",   default="full",
                        choices=["boot", "heartbeat", "full", "rapid", "fault", "multi"],
                        help="Simulation scenario")
    parser.add_argument("--connectors", default=2, type=int,
                        help="Number of connectors to simulate")
    parser.add_argument("--power-kw",   default=60.0, type=float,
                        help="Charger power in kW")
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}"
    sim = ChargerSimulator(
        charger_id=args.charger_id,
        server_url=url,
        connector_count=args.connectors,
        power_kw=args.power_kw,
    )
    await sim.run_scenario(args.scenario)


if __name__ == "__main__":
    asyncio.run(cli_main())
