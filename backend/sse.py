"""
Server-Sent Events (SSE) — live station availability broadcast.

Architecture:
  - A global in-memory queue dict maps client_id → Queue
  - broadcast_availability() pushes a JSON event to ALL connected queues
  - /api/sse/availability streams events to each connected client

This is threading-safe for Flask's default threaded WSGI server.
For production with gunicorn, use --worker-class=gthread.
"""

import json
import queue
import threading
import time
from flask import Blueprint, Response, stream_with_context, request
from flask_jwt_extended import decode_token

sse_bp = Blueprint("sse", __name__)

# Global subscriber registry
_lock = threading.Lock()
_subscribers: dict[str, queue.Queue] = {}


def _register() -> tuple[str, queue.Queue]:
    """Add a new SSE subscriber. Returns (client_id, q)."""
    client_id = str(id(threading.current_thread())) + str(time.monotonic_ns())
    q = queue.Queue(maxsize=50)
    with _lock:
        _subscribers[client_id] = q
    return client_id, q


def _unregister(client_id: str):
    with _lock:
        _subscribers.pop(client_id, None)


def broadcast_availability(station_id: int, available: int, total: int):
    """
    Push an availability update to all connected SSE clients.
    Called from driver.py when a session starts/ends,
    and from operator.py when a charger point status changes.
    """
    payload = json.dumps({
        "type": "availability",
        "station_id": station_id,
        "available_points": available,
        "total_points": total,
    })
    with _lock:
        dead = []
        for cid, q in _subscribers.items():
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(cid)
        for cid in dead:
            _subscribers.pop(cid, None)


def broadcast_point_status(station_id: int, point_id: int, status: str, available: int, total: int):
    """Broadcast an individual charger-point status change."""
    payload = json.dumps({
        "type": "point_status",
        "station_id": station_id,
        "point_id": point_id,
        "status": status,
        "available_points": available,
        "total_points": total,
    })
    with _lock:
        dead = []
        for cid, q in _subscribers.items():
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(cid)
        for cid in dead:
            _subscribers.pop(cid, None)


def _event_stream(q: queue.Queue):
    """Generator that yields SSE-formatted strings from the queue."""
    # Send initial heartbeat so the browser knows the stream is alive
    yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"
    while True:
        try:
            payload = q.get(timeout=25)
            yield f"data: {payload}\n\n"
        except queue.Empty:
            # Heartbeat keepalive every 25 s to prevent proxy timeouts
            yield ": keepalive\n\n"


@sse_bp.route("/availability")
def availability_stream():
    """
    GET /api/sse/availability
    Optional query param: token=<JWT>  (for environments that can't set headers)

    Streams JSON events:
      data: {"type":"availability","station_id":1,"available_points":3,"total_points":6}
      data: {"type":"point_status","station_id":1,"point_id":4,"status":"faulted",...}
    """
    # Optional JWT auth — accept token via query param or Authorization header
    token_param = request.args.get("token")
    if token_param:
        try:
            decode_token(token_param)   # validates signature & expiry
        except Exception:
            return Response("Unauthorized", status=401)

    client_id, q = _register()

    def generate():
        try:
            yield from _event_stream(q)
        finally:
            _unregister(client_id)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@sse_bp.route("/ping")
def ping():
    return {"subscribers": len(_subscribers), "status": "ok"}
