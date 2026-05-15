"""
ChargeNexus OCPP 1.6 Central System
====================================
Runs as a standalone asyncio process on port 9000.
Each Charge Point connects via:
    ws://<host>:9000/ocpp/<charger_id>

The charger_id must match an OcppCharger.charger_id row in the DB.
Unknown chargers are rejected after BootNotification (RegistrationStatus=Rejected).

Run with (from backend/ directory):
    python ocpp/server.py
"""

import sys
import pathlib
# Ensure the backend/ directory is on sys.path so `ocpp` and `database` are importable
_BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import websockets
from websockets.asyncio.server import ServerConnection   # websockets 13.x API

# ── local imports ─────────────────────────────────────────────────────────────
from ocpp.constants import (
    MsgType, CPAction, CSAction,
    ChargePointStatus, RegistrationStatus, AuthorizationStatus,
    AvailabilityType, AvailabilityStatus, ResetType, ResetStatus,
    RemoteStartStopStatus, Reason,
    OCPP_STATUS_MAP, AVAILABLE_STATUSES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OCPP] %(levelname)s  %(message)s",
)
log = logging.getLogger("ocpp.server")

# ── Flask app context for DB access ──────────────────────────────────────────
# We import the Flask app and push its context so SQLAlchemy models work inside
# the asyncio event loop.  DB calls are run in a thread pool to avoid blocking.

_flask_app = None

def _get_flask_app():
    global _flask_app
    if _flask_app is None:
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
        from app import create_app
        _flask_app = create_app()
    return _flask_app


async def _run_in_context(fn, *args, **kwargs):
    """Run a synchronous DB function inside Flask app context in a thread."""
    loop = asyncio.get_event_loop()
    app = _get_flask_app()

    def _wrapper():
        with app.app_context():
            return fn(*args, **kwargs)

    return await loop.run_in_executor(None, _wrapper)


# ── In-memory connection registry ─────────────────────────────────────────────
# charger_id (str) → ChargerConnection instance
_connections: dict[str, "ChargerConnection"] = {}


def get_connected_chargers() -> list[dict]:
    return [c.info() for c in _connections.values()]


async def send_command(charger_id: str, action: str, payload: dict) -> Optional[dict]:
    """Called from Flask routes to send a CS→CP command to a connected charger."""
    conn = _connections.get(charger_id)
    if not conn:
        return None
    return await conn.call(action, payload)


# ── DB helpers (run in thread pool) ──────────────────────────────────────────

def _db_get_charger(charger_id: str):
    from database import OcppCharger
    return OcppCharger.query.filter_by(charger_id=charger_id).first()


def _db_register_charger(charger_id: str, vendor: str, model: str,
                          serial: str, firmware: str, iccid: str, imsi: str):
    from database import db, OcppCharger
    charger = OcppCharger.query.filter_by(charger_id=charger_id).first()
    if not charger:
        log.warning("Unknown charger '%s' — rejecting boot", charger_id)
        return None
    charger.vendor = vendor
    charger.model = model
    charger.serial_number = serial
    charger.firmware_version = firmware
    charger.iccid = iccid
    charger.imsi = imsi
    charger.last_boot = datetime.utcnow()
    charger.ocpp_status = "online"
    db.session.commit()
    return charger


def _db_heartbeat(charger_id: str):
    from database import db, OcppCharger
    OcppCharger.query.filter_by(charger_id=charger_id).update(
        {"last_heartbeat": datetime.utcnow()}
    )
    db.session.commit()


def _db_status_notification(charger_id: str, connector_id: int,
                             ocpp_status: str, error_code: str, info: str):
    from database import db, OcppCharger, ChargerPoint, ChargingStation
    from sse import broadcast_point_status

    charger = OcppCharger.query.filter_by(charger_id=charger_id).first()
    if not charger:
        return

    internal_status = OCPP_STATUS_MAP.get(ocpp_status, "unknown")

    if connector_id == 0:
        # connector_id 0 = the charge point box itself
        charger.ocpp_status = "online" if ocpp_status != "Faulted" else "faulted"
        db.session.commit()
        return

    # Map connector_id to ChargerPoint (connector_id 1-based, point_number 1-based)
    point = ChargerPoint.query.filter_by(
        station_id=charger.station_id,
        point_number=connector_id
    ).first()

    if point:
        point.status = internal_status
        point.fault_code = error_code if error_code != "NoError" else None
        point.last_heartbeat = datetime.utcnow()
        db.session.flush()

        # Recalculate station available_points
        station = ChargingStation.query.get(charger.station_id)
        if station:
            available = ChargerPoint.query.filter_by(
                station_id=station.id, status="available"
            ).count()
            station.available_points = available
            db.session.commit()
            broadcast_point_status(station.id, point.id, internal_status,
                                   available, station.total_points)


def _db_start_transaction(charger_id: str, connector_id: int,
                           id_tag: str, meter_start: int, timestamp: str) -> dict:
    from database import db, OcppCharger, ChargerPoint, ChargingSession, ChargingStation, User
    charger = OcppCharger.query.filter_by(charger_id=charger_id).first()
    if not charger:
        return {"transaction_id": -1, "id_tag_info": {"status": "Invalid"}}

    # Find driver by id_tag (we use user email or phone as RFID tag)
    driver = (User.query.filter_by(email=id_tag).first() or
              User.query.filter_by(phone=id_tag).first())

    session = ChargingSession(
        driver_id=driver.id if driver else 0,
        station_id=charger.station_id,
        start_time=datetime.utcnow(),
        status="active",
        payment_method="RFID" if driver else "Unknown",
    )
    db.session.add(session)
    db.session.flush()

    # Link point to session
    point = ChargerPoint.query.filter_by(
        station_id=charger.station_id, point_number=connector_id
    ).first()
    if point:
        point.status = "occupied"
        point.current_session_id = session.id

    db.session.commit()
    log.info("Transaction started: session=%d charger=%s connector=%d id_tag=%s meter=%d Wh",
             session.id, charger_id, connector_id, id_tag, meter_start)

    return {
        "transaction_id": session.id,
        "id_tag_info": {"status": AuthorizationStatus.ACCEPTED},
    }


def _db_stop_transaction(charger_id: str, transaction_id: int,
                          meter_stop: int, timestamp: str, reason: str,
                          id_tag: str) -> dict:
    from database import db, OcppCharger, ChargerPoint, ChargingSession, ChargingStation, DriverWallet, WalletTransaction
    from sse import broadcast_availability

    session = ChargingSession.query.get(transaction_id)
    if not session:
        return {"id_tag_info": {"status": "Invalid"}}

    charger = OcppCharger.query.filter_by(charger_id=charger_id).first()

    session.end_time = datetime.utcnow()
    session.status = "completed"

    # Calculate energy from meter values (Wh → kWh)
    energy_kwh = round(meter_stop / 1000, 3) if meter_stop else 0
    session.energy_kwh = energy_kwh

    station = ChargingStation.query.get(session.station_id)
    price = station.price_per_kwh if station else 40
    session.amount_inr = round(energy_kwh * price, 2)

    # Free the connector
    point = ChargerPoint.query.filter_by(
        station_id=session.station_id, current_session_id=transaction_id
    ).first()
    if point:
        point.status = "available"
        point.current_session_id = None
        point.total_sessions += 1
        point.total_energy_kwh = round(point.total_energy_kwh + energy_kwh, 3)

    # Credit/debit wallet if we have a known driver
    if session.driver_id:
        wallet = DriverWallet.query.filter_by(driver_id=session.driver_id).first()
        if wallet:
            wallet.balance = round(wallet.balance - session.amount_inr, 2)
            wallet.reward_points += int(energy_kwh * 2)
            db.session.add(WalletTransaction(
                driver_id=session.driver_id, amount=-session.amount_inr,
                txn_type="debit", status="success",
                notes=f"OCPP session #{transaction_id} at {station.name if station else 'Unknown'}"
            ))

    if station:
        available = ChargerPoint.query.filter_by(
            station_id=station.id, status="available"
        ).count()
        station.available_points = available

    db.session.commit()

    if station:
        broadcast_availability(station.id, station.available_points, station.total_points)

    log.info("Transaction stopped: session=%d energy=%.3fkWh amount=₹%.2f reason=%s",
             transaction_id, energy_kwh, session.amount_inr, reason)

    return {"id_tag_info": {"status": AuthorizationStatus.ACCEPTED}}


def _db_meter_values(charger_id: str, connector_id: int,
                     transaction_id: int, sampled_values: list):
    from database import db, MeterReading
    readings = []
    for sv in sampled_values:
        try:
            readings.append(MeterReading(
                charger_id=charger_id,
                connector_id=connector_id,
                transaction_id=transaction_id,
                measurand=sv.get("measurand", "Energy.Active.Import.Register"),
                value=float(sv.get("value", 0)),
                unit=sv.get("unit", "Wh"),
                context=sv.get("context", "Sample.Periodic"),
                recorded_at=datetime.utcnow(),
            ))
        except (ValueError, TypeError):
            pass
    if readings:
        db.session.bulk_save_objects(readings)
        db.session.commit()


def _db_authorize(id_tag: str) -> str:
    from database import User
    user = (User.query.filter_by(email=id_tag).first() or
            User.query.filter_by(phone=id_tag).first())
    return AuthorizationStatus.ACCEPTED if user else AuthorizationStatus.INVALID


def _db_set_offline(charger_id: str):
    from database import db, OcppCharger
    OcppCharger.query.filter_by(charger_id=charger_id).update(
        {"ocpp_status": "offline", "last_heartbeat": datetime.utcnow()}
    )
    db.session.commit()


# ── ChargerConnection — one instance per connected charger ────────────────────

class ChargerConnection:
    """
    Manages the WebSocket connection to a single Charge Point.
    Handles incoming CP→CS messages and sends CS→CP commands.
    """

    def __init__(self, charger_id: str, websocket: ServerConnection):
        self.charger_id = charger_id
        self.ws = websocket
        self.registered = False
        self.vendor = ""
        self.model = ""
        self.connected_at = datetime.utcnow()
        # Pending outgoing calls awaiting CALLRESULT: msg_id → asyncio.Future
        self._pending: dict[str, asyncio.Future] = {}

    def info(self) -> dict:
        remote = getattr(self.ws, "remote_address", None) or getattr(self.ws, "remote_address", "unknown")
        return {
            "charger_id": self.charger_id,
            "vendor": self.vendor,
            "model": self.model,
            "registered": self.registered,
            "connected_at": self.connected_at.isoformat(),
            "remote_address": str(remote),
        }

    # ── send a CS→CP command and await the response ──────────────────────────

    async def call(self, action: str, payload: dict) -> dict:
        msg_id = str(uuid.uuid4())
        frame = json.dumps([MsgType.CALL, msg_id, action, payload])
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[msg_id] = future
        await self.ws.send(frame)
        log.debug("→ CP [%s] %s %s", self.charger_id, action, payload)
        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise TimeoutError(f"Charger {self.charger_id} did not respond to {action} within 30s")

    # ── send a CALLRESULT back to the charger ────────────────────────────────

    async def _respond(self, msg_id: str, payload: dict):
        frame = json.dumps([MsgType.CALLRESULT, msg_id, payload])
        await self.ws.send(frame)
        log.debug("← CS [%s] CALLRESULT %s", self.charger_id, payload)

    async def _respond_error(self, msg_id: str, error_code: str, description: str):
        frame = json.dumps([MsgType.CALLERROR, msg_id, error_code, description, {}])
        await self.ws.send(frame)

    # ── main receive loop ────────────────────────────────────────────────────

    async def run(self):
        _connections[self.charger_id] = self
        log.info("Charger connected: %s from %s", self.charger_id,
                 getattr(self.ws, "remote_address", "unknown"))
        try:
            async for raw in self.ws:
                await self._handle_message(raw)
        except websockets.exceptions.ConnectionClosed as e:
            log.info("Charger disconnected: %s (%s)", self.charger_id, e)
        except Exception as e:
            log.error("Unexpected error from %s: %s", self.charger_id, e)
        finally:
            _connections.pop(self.charger_id, None)
            await _run_in_context(_db_set_offline, self.charger_id)

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Invalid JSON from %s: %s", self.charger_id, raw[:200])
            return

        if not isinstance(msg, list) or len(msg) < 3:
            return

        msg_type = msg[0]
        msg_id   = msg[1]

        if msg_type == MsgType.CALL:
            action  = msg[2]
            payload = msg[3] if len(msg) > 3 else {}
            log.info("← CP [%s] %s", self.charger_id, action)
            await self._dispatch(msg_id, action, payload)

        elif msg_type == MsgType.CALLRESULT:
            payload = msg[2] if len(msg) > 2 else {}
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                future.set_result(payload)

        elif msg_type == MsgType.CALLERROR:
            error_code = msg[2] if len(msg) > 2 else "Unknown"
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                future.set_exception(RuntimeError(f"OCPP error {error_code}"))

    # ── action dispatcher ────────────────────────────────────────────────────

    async def _dispatch(self, msg_id: str, action: str, payload: dict):
        handlers = {
            CPAction.BOOT_NOTIFICATION:   self._handle_boot,
            CPAction.HEARTBEAT:           self._handle_heartbeat,
            CPAction.STATUS_NOTIFICATION: self._handle_status_notification,
            CPAction.START_TRANSACTION:   self._handle_start_transaction,
            CPAction.STOP_TRANSACTION:    self._handle_stop_transaction,
            CPAction.METER_VALUES:        self._handle_meter_values,
            CPAction.AUTHORIZE:           self._handle_authorize,
            CPAction.DATA_TRANSFER:       self._handle_data_transfer,
            CPAction.FIRMWARE_STATUS:     self._handle_firmware_status,
            CPAction.DIAGNOSTICS_STATUS:  self._handle_diagnostics_status,
        }
        handler = handlers.get(action)
        if handler:
            try:
                await handler(msg_id, payload)
            except Exception as e:
                log.error("Error handling %s from %s: %s", action, self.charger_id, e, exc_info=True)
                await self._respond_error(msg_id, "InternalError", str(e))
        else:
            log.warning("Unknown action '%s' from %s", action, self.charger_id)
            await self._respond_error(msg_id, "NotImplemented", f"Action {action} not supported")

    # ── individual action handlers ───────────────────────────────────────────

    async def _handle_boot(self, msg_id: str, p: dict):
        charger = await _run_in_context(
            _db_register_charger,
            self.charger_id,
            p.get("chargePointVendor", ""),
            p.get("chargePointModel", ""),
            p.get("chargePointSerialNumber", ""),
            p.get("firmwareVersion", ""),
            p.get("iccid", ""),
            p.get("imsi", ""),
        )
        if charger is None:
            await self._respond(msg_id, {
                "status": RegistrationStatus.REJECTED,
                "currentTime": datetime.utcnow().isoformat() + "Z",
                "interval": 300,
            })
            await self.ws.close()
            return

        self.registered = True
        self.vendor = p.get("chargePointVendor", "")
        self.model  = p.get("chargePointModel", "")

        await self._respond(msg_id, {
            "status": RegistrationStatus.ACCEPTED,
            "currentTime": datetime.utcnow().isoformat() + "Z",
            "interval": 60,   # request heartbeat every 60 seconds
        })
        log.info("Boot accepted: %s %s %s", self.charger_id, self.vendor, self.model)

    async def _handle_heartbeat(self, msg_id: str, p: dict):
        await _run_in_context(_db_heartbeat, self.charger_id)
        await self._respond(msg_id, {"currentTime": datetime.utcnow().isoformat() + "Z"})

    async def _handle_status_notification(self, msg_id: str, p: dict):
        connector_id = p.get("connectorId", 0)
        status       = p.get("status", "")
        error_code   = p.get("errorCode", "NoError")
        info         = p.get("info", "")

        await _run_in_context(
            _db_status_notification,
            self.charger_id, connector_id, status, error_code, info
        )
        log.info("Status: %s connector=%d → %s (%s)", self.charger_id, connector_id, status, error_code)
        await self._respond(msg_id, {})

    async def _handle_start_transaction(self, msg_id: str, p: dict):
        result = await _run_in_context(
            _db_start_transaction,
            self.charger_id,
            p.get("connectorId", 1),
            p.get("idTag", ""),
            p.get("meterStart", 0),
            p.get("timestamp", ""),
        )
        await self._respond(msg_id, result)

    async def _handle_stop_transaction(self, msg_id: str, p: dict):
        result = await _run_in_context(
            _db_stop_transaction,
            self.charger_id,
            p.get("transactionId", -1),
            p.get("meterStop", 0),
            p.get("timestamp", ""),
            p.get("reason", Reason.OTHER),
            p.get("idTag", ""),
        )
        await self._respond(msg_id, result)

    async def _handle_meter_values(self, msg_id: str, p: dict):
        connector_id    = p.get("connectorId", 1)
        transaction_id  = p.get("transactionId")
        meter_value_list = p.get("meterValue", [])

        sampled = []
        for mv in meter_value_list:
            for sv in mv.get("sampledValue", []):
                sampled.append(sv)

        if sampled:
            await _run_in_context(
                _db_meter_values, self.charger_id, connector_id, transaction_id, sampled
            )
        await self._respond(msg_id, {})

    async def _handle_authorize(self, msg_id: str, p: dict):
        id_tag = p.get("idTag", "")
        status = await _run_in_context(_db_authorize, id_tag)
        await self._respond(msg_id, {"idTagInfo": {"status": status}})

    async def _handle_data_transfer(self, msg_id: str, p: dict):
        log.info("DataTransfer from %s: vendor=%s msgId=%s",
                 self.charger_id, p.get("vendorId"), p.get("messageId"))
        await self._respond(msg_id, {"status": "Accepted"})

    async def _handle_firmware_status(self, msg_id: str, p: dict):
        log.info("FirmwareStatus from %s: %s", self.charger_id, p.get("status"))
        await self._respond(msg_id, {})

    async def _handle_diagnostics_status(self, msg_id: str, p: dict):
        log.info("DiagnosticsStatus from %s: %s", self.charger_id, p.get("status"))
        await self._respond(msg_id, {})


# ── WebSocket server entry point ──────────────────────────────────────────────

async def _handle_connection(websocket: ServerConnection):
    """
    Called for each new WebSocket connection.
    Path format: /ocpp/<charger_id>
    In websockets 13.x, path is at websocket.request.path
    """
    # Extract path from the HTTP upgrade request
    path = getattr(websocket, "request", None)
    if path is not None:
        path = path.path
    else:
        # Fallback for older websockets API
        path = getattr(websocket, "path", "/")

    # Extract charger_id from path
    parts = path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "ocpp":
        log.warning("Invalid path '%s' — closing", path)
        await websocket.close(1008, "Invalid path. Use /ocpp/<charger_id>")
        return

    charger_id = parts[1]

    # Check subprotocol negotiation (OCPP 1.6 requires ocpp1.6)
    subprotocol = getattr(websocket, "subprotocol", None)
    if subprotocol and subprotocol != "ocpp1.6":
        log.warning("Charger %s requested unsupported subprotocol: %s", charger_id, subprotocol)

    conn = ChargerConnection(charger_id, websocket)
    await conn.run()


async def main():
    host = os.getenv("OCPP_HOST", "0.0.0.0")
    port = int(os.getenv("OCPP_PORT", "9000"))

    log.info("ChargeNexus OCPP 1.6 Central System starting on ws://%s:%d/ocpp/<charger_id>", host, port)

    # websockets 13.x: use websockets.asyncio.server.serve
    from websockets.asyncio.server import serve

    async with serve(
        _handle_connection,
        host,
        port,
        subprotocols=["ocpp1.6"],
        ping_interval=20,
        ping_timeout=60,
        max_size=1_048_576,   # 1 MB max message size
    ):
        log.info("OCPP server ready. Waiting for charger connections...")
        await asyncio.Future()   # run forever


if __name__ == "__main__":
    asyncio.run(main())
