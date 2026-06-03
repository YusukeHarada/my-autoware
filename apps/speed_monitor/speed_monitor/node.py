"""
Speed monitor node for Autoware.

Subscribes to vehicle velocity and publishes alerts when limits are exceeded.
Logs events to a CSV file for post-analysis.
"""

import csv
import pathlib
import time

import rclpy
from rclpy.node import Node
from autoware_auto_vehicle_msgs.msg import VelocityReport
from std_msgs.msg import String


SPEED_LIMIT_MS = 13.89  # 50 km/h in m/s


class SpeedMonitorNode(Node):
    def __init__(self):
        super().__init__("speed_monitor")

        self.declare_parameter("speed_limit_kmh", 50.0)
        self.declare_parameter("log_path", "/tmp/speed_log.csv")

        limit_kmh = self.get_parameter("speed_limit_kmh").value
        self._limit_ms = limit_kmh / 3.6

        log_path = pathlib.Path(self.get_parameter("log_path").value)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._csv = open(log_path, "w", newline="")
        self._writer = csv.writer(self._csv)
        self._writer.writerow(["timestamp", "speed_ms", "speed_kmh", "alert"])

        self._alert_pub = self.create_publisher(String, "/speed_monitor/alert", 10)

        self.create_subscription(
            VelocityReport,
            "/vehicle/status/velocity_status",
            self._on_velocity,
            10,
        )

        self.get_logger().info(
            f"SpeedMonitor ready. Limit: {limit_kmh:.1f} km/h | Log: {log_path}"
        )

    def _on_velocity(self, msg: VelocityReport):
        speed_ms = abs(msg.longitudinal_velocity)
        speed_kmh = speed_ms * 3.6
        over_limit = speed_ms > self._limit_ms

        self._writer.writerow(
            [time.time(), f"{speed_ms:.3f}", f"{speed_kmh:.1f}", int(over_limit)]
        )
        self._csv.flush()

        if over_limit:
            alert_msg = String()
            alert_msg.data = (
                f"SPEED ALERT: {speed_kmh:.1f} km/h "
                f"(limit {self._limit_ms * 3.6:.0f} km/h)"
            )
            self._alert_pub.publish(alert_msg)
            self.get_logger().warn(alert_msg.data)

    def destroy_node(self):
        self._csv.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = SpeedMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
