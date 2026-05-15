"""
OCPP Management Routes — operator REST API for managing physical chargers.

GET  /api/ocpp/chargers                      list all registered charger boxes
POST /api/ocpp/chargers                      register a new charger box
GET  /api/ocpp/chargers/<charger_id>         get charger + connector status
PUT  /api/ocpp/chargers/<charger_id>         update charger metadata
GET  /api/ocpp/chargers/<charger_id>/status  live connection status
POST /api/ocpp/chargers/<charger_id>/remote-start    send RemoteStartTransaction
POST /api/ocpp/chargers/<charger_id>/remote-stop     send RemoteStopTransaction
POST /api/ocpp/chargers/<charger_id>/change-avail    send ChangeAvailability
POST /api/ocpp/chargers/<charger_id>/reset           send Reset
POST /api/ocpp/chargers/<charger_id>/get-config      send GetConfiguration
GET  /api/ocpp/chargers/<charger_id>/meter-readings  last N meter readings
GET  /api/ocpp/connected                     list currently connected chargers
"""

import asyncio
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, OcppCharger, MeterReading, ChargingStation, ChargerPoint, User

ocpp_bp = Blueprint("ocpp", __name__)


def _get_operator_id():
    return int(get_jwt_identity())


def _require_charger(charger_id: str, operator_id: int):
    """Return charger if it belongs to a station owned by this operator."""
    charger = OcppCharger.query.filter_by(charger_id=charger_id).first_or_404()
    station = ChargingStation.query.filter_by(
        id=charger.station_id, operator_id=operator_id
    ).first()
    if not station:
        return None, jsonify({"error": "Unauthorized"}), 403
    return charger, None, None


def _send_ocpp_command(charger_id: str, action: str, payload: dict):
    """
    Bridge between Flask (sync) and the asyncio OCPP server.
    The OCPP server runs in a separate process, so we use a simple
    inter-process communication via the shared asyncio event loop
    if running in the same process, or via HTTP to the OCPP management API.

    For simplicity in this implementation: if the OCPP server is
    imported in the same process, call it directly. Otherwise return
    a 'server_offline' error gracefully.
    """
    try:
        from ocpp.server import send_command, _connections
        # Check if charger is connected
        if charger_id not in _connections:
            return None, "Charger not connected to OCPP server"

        # Run the async call in a new event loop (Flask is sync)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(send_command(charger_id, action, payload))
            return result, None
        finally:
            loop.close()
    except Exception as e:
        current_app.logger.warning("OCPP command failed: %s", e)
        return None, str(e)


# ── Charger registry ──────────────────────────────────────────────────────────

@ocpp_bp.route("/chargers", methods=["GET"])
@jwt_required()
def list_chargers():
    operator_id = _get_operator_id()
    stations = ChargingStation.query.filter_by(operator_id=operator_id).all()
    sids = [s.id for s in stations]
    chargers = OcppCharger.query.filter(OcppCharger.station_id.in_(sids)).all()

    # Enrich with live connection status
    try:
        from ocpp.server import _connections
        connected_ids = set(_connections.keys())
    except Exception:
        connected_ids = set()

    result = []
    for c in chargers:
        d = c.to_dict()
        d["is_connected"] = c.charger_id in connected_ids
        # Connector status
        points = ChargerPoint.query.filter_by(station_id=c.station_id).all()
        d["connectors"] = [p.to_dict() for p in points]
        result.append(d)

    return jsonify(result)


@ocpp_bp.route("/chargers", methods=["POST"])
@jwt_required()
def register_charger():
    operator_id = _get_operator_id()
    data = request.get_json() or {}

    charger_id = (data.get("charger_id") or "").strip()
    station_id = data.get("station_id")

    if not charger_id or not station_id:
        return jsonify({"error": "charger_id and station_id are required"}), 422

    # Validate station belongs to this operator
    station = ChargingStation.query.filter_by(
        id=station_id, operator_id=operator_id
    ).first()
    if not station:
        return jsonify({"error": "Station not found or unauthorized"}), 403

    if OcppCharger.query.filter_by(charger_id=charger_id).first():
        return jsonify({"error": f"Charger ID '{charger_id}' already registered"}), 409

    charger = OcppCharger(
        charger_id=charger_id,
        station_id=station_id,
        notes=data.get("notes", ""),
    )
    db.session.add(charger)
    db.session.commit()
    return jsonify(charger.to_dict()), 201


@ocpp_bp.route("/chargers/<charger_id>", methods=["GET"])
@jwt_required()
def get_charger(charger_id):
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    try:
        from ocpp.server import _connections
        is_connected = charger_id in _connections
        conn_info = _connections[charger_id].info() if is_connected else None
    except Exception:
        is_connected = False
        conn_info = None

    points = ChargerPoint.query.filter_by(station_id=charger.station_id).all()
    d = charger.to_dict()
    d["is_connected"] = is_connected
    d["connection_info"] = conn_info
    d["connectors"] = [p.to_dict() for p in points]
    return jsonify(d)


@ocpp_bp.route("/chargers/<charger_id>", methods=["PUT"])
@jwt_required()
def update_charger(charger_id):
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    data = request.get_json() or {}
    if "notes" in data:
        charger.notes = data["notes"]
    if "heartbeat_interval" in data:
        charger.heartbeat_interval = int(data["heartbeat_interval"])
    db.session.commit()
    return jsonify(charger.to_dict())


@ocpp_bp.route("/chargers/<charger_id>", methods=["DELETE"])
@jwt_required()
def delete_charger(charger_id):
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code
    db.session.delete(charger)
    db.session.commit()
    return jsonify({"deleted": True})


# ── Remote commands ───────────────────────────────────────────────────────────

@ocpp_bp.route("/chargers/<charger_id>/remote-start", methods=["POST"])
@jwt_required()
def remote_start(charger_id):
    """Send RemoteStartTransaction to a connected charger."""
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    data = request.get_json() or {}
    connector_id = data.get("connector_id", 1)
    id_tag       = data.get("id_tag", "operator@chargenexus.in")

    result, error = _send_ocpp_command(charger_id, "RemoteStartTransaction", {
        "connectorId": connector_id,
        "idTag": id_tag,
    })

    if error:
        return jsonify({"error": error, "tip": "Ensure OCPP server is running and charger is connected"}), 503

    return jsonify({"status": result.get("status"), "connector_id": connector_id})


@ocpp_bp.route("/chargers/<charger_id>/remote-stop", methods=["POST"])
@jwt_required()
def remote_stop(charger_id):
    """Send RemoteStopTransaction to stop an active session."""
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    data = request.get_json() or {}
    transaction_id = data.get("transaction_id")
    if not transaction_id:
        return jsonify({"error": "transaction_id required"}), 422

    result, error = _send_ocpp_command(charger_id, "RemoteStopTransaction", {
        "transactionId": int(transaction_id),
    })
    if error:
        return jsonify({"error": error}), 503

    return jsonify({"status": result.get("status")})


@ocpp_bp.route("/chargers/<charger_id>/change-availability", methods=["POST"])
@jwt_required()
def change_availability(charger_id):
    """Set connector Operative or Inoperative."""
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    data         = request.get_json() or {}
    connector_id = data.get("connector_id", 0)   # 0 = whole charger
    avail_type   = data.get("type", "Operative")  # Operative|Inoperative

    if avail_type not in ("Operative", "Inoperative"):
        return jsonify({"error": "type must be Operative or Inoperative"}), 422

    result, error = _send_ocpp_command(charger_id, "ChangeAvailability", {
        "connectorId": connector_id,
        "type": avail_type,
    })
    if error:
        return jsonify({"error": error}), 503

    return jsonify({"status": result.get("status")})


@ocpp_bp.route("/chargers/<charger_id>/reset", methods=["POST"])
@jwt_required()
def reset_charger(charger_id):
    """Send a Hard or Soft reset to the charger."""
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    reset_type = (request.get_json() or {}).get("type", "Soft")
    if reset_type not in ("Hard", "Soft"):
        return jsonify({"error": "type must be Hard or Soft"}), 422

    result, error = _send_ocpp_command(charger_id, "Reset", {"type": reset_type})
    if error:
        return jsonify({"error": error}), 503

    return jsonify({"status": result.get("status")})


@ocpp_bp.route("/chargers/<charger_id>/get-configuration", methods=["POST"])
@jwt_required()
def get_configuration(charger_id):
    """Fetch configuration keys from the charger."""
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    keys = (request.get_json() or {}).get("keys", [])
    result, error = _send_ocpp_command(charger_id, "GetConfiguration", {"key": keys})
    if error:
        return jsonify({"error": error}), 503

    return jsonify(result)


@ocpp_bp.route("/chargers/<charger_id>/unlock-connector", methods=["POST"])
@jwt_required()
def unlock_connector(charger_id):
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    connector_id = (request.get_json() or {}).get("connector_id", 1)
    result, error = _send_ocpp_command(charger_id, "UnlockConnector", {"connectorId": connector_id})
    if error:
        return jsonify({"error": error}), 503
    return jsonify({"status": result.get("status")})


# ── Meter readings ────────────────────────────────────────────────────────────

@ocpp_bp.route("/chargers/<charger_id>/meter-readings", methods=["GET"])
@jwt_required()
def meter_readings(charger_id):
    operator_id = _get_operator_id()
    charger, err, code = _require_charger(charger_id, operator_id)
    if err:
        return err, code

    limit       = min(request.args.get("limit", 100, type=int), 500)
    measurand   = request.args.get("measurand")
    connector_id = request.args.get("connector_id", type=int)

    q = MeterReading.query.filter_by(charger_id=charger_id)
    if measurand:
        q = q.filter_by(measurand=measurand)
    if connector_id:
        q = q.filter_by(connector_id=connector_id)

    readings = q.order_by(MeterReading.recorded_at.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in readings])


# ── Live connection status ────────────────────────────────────────────────────

@ocpp_bp.route("/connected", methods=["GET"])
@jwt_required()
def connected_chargers():
    """List all chargers currently connected to the OCPP server."""
    try:
        from ocpp.server import get_connected_chargers
        chargers = get_connected_chargers()
    except Exception as e:
        return jsonify({
            "error": "OCPP server not reachable",
            "detail": str(e),
            "tip": "Start OCPP server with: python ocpp/server.py",
        }), 503

    return jsonify({"connected": chargers, "count": len(chargers)})


@ocpp_bp.route("/server-status", methods=["GET"])
def server_status():
    """Health check for the OCPP server (no auth required)."""
    try:
        from ocpp.server import _connections
        return jsonify({
            "ocpp_server": "running",
            "connected_chargers": len(_connections),
            "charger_ids": list(_connections.keys()),
        })
    except Exception as e:
        return jsonify({"ocpp_server": "offline", "error": str(e)}), 503
