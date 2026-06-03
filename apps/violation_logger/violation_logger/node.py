"""
Traffic violation logger node.

Detects and records:
  - Speed limit violations
  - Sudden braking (deceleration > threshold)
  - Sharp steering (angle rate > threshold)

Violations are published to /violations and written to a JSON log.
"""

import collections
import json
import pathlib
import time

import rclpy
from rclpy.node import Node
from autoware_auto_vehicle_msgs.msg import VelocityReport, SteeringReport
from std_msgs.msg import String


class ViolationLoggerNode(Node):
    def __init__(self):
        super().__init__("violation_logger")

        self.declare_parameter("speed_limit_kmh",     50.0)
        self.declare_parameter("brake_threshold_ms2", -4.0)
        self.declare_parameter("steer_rate_threshold", 0.5)   # rad/s
        self.declare_parameter("log_path",            "/tmp/violations.json")

        self._limit_ms      = self.get_parameter("speed_limit_kmh").value / 3.6
        self._brake_thresh  = self.get_parameter("brake_threshold_ms2").value
        self._steer_thresh  = self.get_parameter("steer_rate_threshold").value
        log_path = pathlib.Path(self.get_parameter("log_path").value)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_path = log_path

        self._violations: list[dict] = []
        self._speed_history: collections.deque = collections.deque(maxlen=10)
        self._steer_history: collections.deque = collections.deque(maxlen=5)

        self._pub = self.create_publisher(String, "/violations", 10)

        self.create_subscription(
            VelocityReport,
            "/vehicle/status/velocity_status",
            self._on_velocity,
            10,
        )
        self.create_subscription(
            SteeringReport,
            "/vehicle/status/steering_status",
            self._on_steering,
            10,
        )

        self.get_logger().info(f"ViolationLogger ready | log → {log_path}")

    # ----------------------------------------------------------------

    def _on_velocity(self, msg: VelocityReport):
        speed = abs(msg.longitudinal_velocity)
        now = time.time()
        self._speed_history.append((now, speed))

        # --- speed violation ---
        if speed > self._limit_ms:
            self._record("SPEED_VIOLATION", {
                "speed_kmh": round(speed * 3.6, 1),
                "limit_kmh": round(self._limit_ms * 3.6, 1),
            })

        # --- sudden braking ---
        if len(self._speed_history) >= 2:
            dt = now - self._speed_history[-2][0]
            if dt > 0:
                accel = (speed - self._speed_history[-2][1]) / dt
                if accel < self._brake_thresh:
                    self._record("SUDDEN_BRAKE", {
                        "decel_ms2": round(accel, 2),
                        "threshold": self._brake_thresh,
                    })

    def _on_steering(self, msg: SteeringReport):
        now = time.time()
        angle = msg.steering_tire_angle
        self._steer_history.append((now, angle))

        if len(self._steer_history) >= 2:
            dt = now - self._steer_history[-2][0]
            if dt > 0:
                rate = abs(angle - self._steer_history[-2][1]) / dt
                if rate > self._steer_thresh:
                    self._record("SHARP_STEER", {
                        "steer_rate_rads": round(rate, 3),
                        "threshold": self._steer_thresh,
                    })

    # ----------------------------------------------------------------

    def _record(self, vtype: str, detail: dict):
        entry = {"timestamp": time.time(), "type": vtype, **detail}
        self._violations.append(entry)

        # Publish alert
        msg = String()
        msg.data = json.dumps(entry)
        self._pub.publish(msg)
        self.get_logger().warn(f"[{vtype}] {detail}")

        # Flush log
        with open(self._log_path, "w") as f:
            json.dump(self._violations, f, indent=2)

    def destroy_node(self):
        self.get_logger().info(
            f"ViolationLogger stopped. {len(self._violations)} violations recorded."
        )
        super().destroy_node()


def main():
    rclpy.init()
    node = ViolationLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
