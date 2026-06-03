"""
E2E control node.

Subscribes to the front camera, runs the CNN model, and publishes
AckermannControlCommand to /control/command/control_cmd.

The node is meant to REPLACE Autoware's planning + control stacks
in AWSIM experiments. Enable it by setting use_e2e_control:=true in
your launch file and disabling the standard control nodes.
"""

import pathlib

import numpy as np
import torch
from torchvision import transforms

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from autoware_auto_control_msgs.msg import AckermannControlCommand
from cv_bridge import CvBridge

from .model import E2EDriver


_TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Vehicle-specific constants (sample_vehicle)
MAX_STEER_RAD = 0.5236   # 30 deg
MAX_ACCEL_MS2 = 3.0
MAX_DECEL_MS2 = -5.0


class E2EControlNode(Node):
    def __init__(self):
        super().__init__("e2e_control")

        self.declare_parameter("model_path", "")
        self.declare_parameter("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.declare_parameter("target_speed_kmh", 30.0)

        model_path = self.get_parameter("model_path").value
        self._device = torch.device(self.get_parameter("device").value)
        self._target_speed = self.get_parameter("target_speed_kmh").value / 3.6

        self._model = E2EDriver(pretrained=(not model_path)).to(self._device)
        if model_path and pathlib.Path(model_path).exists():
            state = torch.load(model_path, map_location=self._device)
            self._model.load_state_dict(state)
            self.get_logger().info(f"Loaded weights from {model_path}")
        else:
            self.get_logger().warn("No model weights provided — using random (pretrained backbone) weights.")

        self._model.eval()
        self._bridge = CvBridge()

        self._pub = self.create_publisher(
            AckermannControlCommand, "/control/command/control_cmd", 1
        )
        self.create_subscription(
            Image, "/sensing/camera/camera0/image_raw", self._on_image, 1
        )

        self.get_logger().info(
            f"E2EControl ready on {self._device} | target {self._target_speed*3.6:.0f} km/h"
        )

    def _on_image(self, msg: Image):
        cv_img = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        tensor = _TRANSFORM(cv_img).unsqueeze(0).to(self._device)

        with torch.no_grad():
            out = self._model(tensor)[0].cpu().numpy()  # [steer, throttle]

        steer_rad = float(out[0]) * MAX_STEER_RAD
        throttle = float(out[1])  # [-1, 1]
        accel = throttle * (MAX_ACCEL_MS2 if throttle >= 0 else -MAX_DECEL_MS2)

        cmd = AckermannControlCommand()
        cmd.stamp = self.get_clock().now().to_msg()
        cmd.lateral.steering_tire_angle = steer_rad
        cmd.longitudinal.acceleration = accel
        cmd.longitudinal.speed = self._target_speed
        self._pub.publish(cmd)


def main():
    rclpy.init()
    node = E2EControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
