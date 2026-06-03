"""
FastAPI backend for the Autoware Web Dashboard.

Bridges ROS 2 topics to a REST/WebSocket API so a browser can
visualize the ego vehicle's real-time state without RViz.

Endpoints:
  GET  /status          – latest vehicle snapshot (JSON)
  WS   /ws              – live stream of vehicle state (JSON lines)
  GET  /trajectory      – latest planned trajectory (GeoJSON)
  GET  /health          – liveness probe
"""

import asyncio
import json
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from autoware_auto_vehicle_msgs.msg import VelocityReport
from autoware_auto_planning_msgs.msg import Trajectory
from geometry_msgs.msg import PoseWithCovarianceStamped

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Autoware Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- shared state updated by ROS 2 callbacks ----------
_state: dict = {
    "speed_ms": 0.0,
    "speed_kmh": 0.0,
    "position": {"x": 0.0, "y": 0.0},
    "heading": 0.0,
}
_trajectory: list = []
_subscribers: list[WebSocket] = []
_state_lock = threading.Lock()


class DashboardNode(Node):
    def __init__(self):
        super().__init__("dashboard_backend")
        self.create_subscription(
            VelocityReport,
            "/vehicle/status/velocity_status",
            self._on_velocity,
            10,
        )
        self.create_subscription(
            PoseWithCovarianceStamped,
            "/localization/pose_with_covariance",
            self._on_pose,
            10,
        )
        self.create_subscription(
            Trajectory,
            "/planning/scenario_planning/trajectory",
            self._on_trajectory,
            10,
        )

    def _on_velocity(self, msg: VelocityReport):
        with _state_lock:
            _state["speed_ms"] = round(abs(msg.longitudinal_velocity), 2)
            _state["speed_kmh"] = round(_state["speed_ms"] * 3.6, 1)
        asyncio.run_coroutine_threadsafe(_broadcast(), asyncio.get_event_loop())

    def _on_pose(self, msg: PoseWithCovarianceStamped):
        p = msg.pose.pose
        with _state_lock:
            _state["position"]["x"] = round(p.position.x, 3)
            _state["position"]["y"] = round(p.position.y, 3)
            _state["heading"] = round(
                2.0
                * __import__("math").atan2(
                    p.orientation.z, p.orientation.w
                ),
                4,
            )

    def _on_trajectory(self, msg: Trajectory):
        global _trajectory
        _trajectory = [
            {"x": pt.pose.position.x, "y": pt.pose.position.y}
            for pt in msg.points
        ]


async def _broadcast():
    with _state_lock:
        payload = json.dumps(_state)
    dead = []
    for ws in _subscribers:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _subscribers.remove(ws)


# ---------- REST endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    with _state_lock:
        return dict(_state)


@app.get("/trajectory")
def trajectory():
    return {
        "type": "LineString",
        "coordinates": [[pt["x"], pt["y"]] for pt in _trajectory],
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _subscribers.append(ws)
    try:
        while True:
            await asyncio.sleep(1)   # keep connection alive
    except WebSocketDisconnect:
        _subscribers.remove(ws)


# ---------- startup / shutdown ----------

@app.on_event("startup")
def start_ros():
    rclpy.init()
    node = DashboardNode()
    t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    t.start()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
