"""
Dataset collection node.

Records front-camera images and the matching AckermannControlCommand
from a human-driven (or Autoware-driven) AWSIM session.
Saves images as PNG and appends rows to labels.csv.

Usage:
  ros2 run e2e_control collect --ros-args -p out_dir:=/data/awsim_dataset
"""

import csv
import pathlib
import time

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from autoware_auto_control_msgs.msg import AckermannControlCommand
from cv_bridge import CvBridge

MAX_STEER_RAD = 0.5236
MAX_ACCEL_MS2 = 3.0


class CollectNode(Node):
    def __init__(self):
        super().__init__("e2e_collect")
        self.declare_parameter("out_dir", "/tmp/e2e_dataset")

        out = pathlib.Path(self.get_parameter("out_dir").value)
        self._img_dir = out / "images"
        self._img_dir.mkdir(parents=True, exist_ok=True)

        self._csv_file = open(out / "labels.csv", "a", newline="")
        self._writer = csv.writer(self._csv_file)
        if self._csv_file.tell() == 0:
            self._writer.writerow(["filename", "steer", "throttle"])

        self._bridge = CvBridge()
        self._latest_cmd: AckermannControlCommand | None = None
        self._count = 0

        self.create_subscription(
            AckermannControlCommand,
            "/control/command/control_cmd",
            lambda m: setattr(self, "_latest_cmd", m),
            1,
        )
        self.create_subscription(
            Image,
            "/sensing/camera/camera0/image_raw",
            self._on_image,
            1,
        )
        self.get_logger().info(f"Collecting dataset to {out}")

    def _on_image(self, msg: Image):
        if self._latest_cmd is None:
            return

        cmd = self._latest_cmd
        steer = cmd.lateral.steering_tire_angle / MAX_STEER_RAD
        throttle = cmd.longitudinal.acceleration / MAX_ACCEL_MS2
        steer = max(-1.0, min(1.0, steer))
        throttle = max(-1.0, min(1.0, throttle))

        fname = f"{int(time.time() * 1000):016d}.png"
        cv_img = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        cv2.imwrite(str(self._img_dir / fname), cv_img)
        self._writer.writerow([fname, f"{steer:.6f}", f"{throttle:.6f}"])
        self._csv_file.flush()

        self._count += 1
        if self._count % 100 == 0:
            self.get_logger().info(f"Collected {self._count} samples")

    def destroy_node(self):
        self._csv_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = CollectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
