"""
Perception evaluator node.

Compares Autoware's detected objects against AWSIM ground-truth objects
using IoU-based matching and accumulates per-class precision / recall.

Topics:
  Subscribe: /perception/object_recognition/detection/objects
             (autoware_auto_perception_msgs/DetectedObjects)
  Subscribe: /awsim/ground_truth/objects
             (autoware_auto_perception_msgs/DetectedObjects)
  Publish:   /perception_eval/metrics  (std_msgs/String — JSON)
"""

import json
import math
import time

import rclpy
from rclpy.node import Node
from autoware_auto_perception_msgs.msg import DetectedObjects
from std_msgs.msg import String


IOU_THRESHOLD = 0.3   # match threshold for 3-D bounding boxes


# ---- geometry helpers ----

def _bbox_corners_2d(cx: float, cy: float, w: float, l: float, yaw: float):
    """Return the 4 corners of an axis-aligned (yaw-ignored) bounding box."""
    hw, hl = w / 2.0, l / 2.0
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    corners = []
    for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        dx = sx * hw * cos_y - sy * hl * sin_y
        dy = sx * hw * sin_y + sy * hl * cos_y
        corners.append((cx + dx, cy + dy))
    return corners


def _aabb(obj) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box (xmin, ymin, xmax, ymax) from DetectedObject."""
    p = obj.kinematics.pose_with_covariance.pose.position
    s = obj.shape.dimensions
    return (
        p.x - s.x / 2, p.y - s.y / 2,
        p.x + s.x / 2, p.y + s.y / 2,
    )


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = _aabb(a)
    bx1, by1, bx2, by2 = _aabb(b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def _label(obj) -> str:
    """Map classification label enum to string."""
    label_map = {
        0: "UNKNOWN", 1: "CAR", 2: "TRUCK", 3: "BUS",
        4: "BICYCLE", 5: "MOTORBIKE", 6: "PEDESTRIAN",
    }
    if not obj.classification:
        return "UNKNOWN"
    return label_map.get(obj.classification[0].label, "UNKNOWN")


# ---- evaluator ----

class PerceptionEvalNode(Node):
    def __init__(self):
        super().__init__("perception_eval")
        self.declare_parameter("iou_threshold", IOU_THRESHOLD)
        self.declare_parameter("report_interval_s", 5.0)

        self._iou_thresh = self.get_parameter("iou_threshold").value
        interval = self.get_parameter("report_interval_s").value

        # Accumulators: {class: {"tp": int, "fp": int, "fn": int}}
        self._stats: dict[str, dict[str, int]] = {}
        self._latest_gt: list = []
        self._latest_det: list = []

        self._pub = self.create_publisher(String, "/perception_eval/metrics", 10)
        self.create_timer(interval, self._publish_metrics)

        self.create_subscription(
            DetectedObjects,
            "/perception/object_recognition/detection/objects",
            self._on_detection,
            10,
        )
        self.create_subscription(
            DetectedObjects,
            "/awsim/ground_truth/objects",
            self._on_ground_truth,
            10,
        )

        self.get_logger().info(
            f"PerceptionEval ready | IoU≥{self._iou_thresh} | "
            f"report every {interval}s"
        )

    def _on_detection(self, msg: DetectedObjects):
        self._latest_det = list(msg.objects)
        self._evaluate()

    def _on_ground_truth(self, msg: DetectedObjects):
        self._latest_gt = list(msg.objects)

    def _evaluate(self):
        gt_objects  = self._latest_gt
        det_objects = self._latest_det
        if not gt_objects and not det_objects:
            return

        matched_gt  = set()
        matched_det = set()

        for di, det in enumerate(det_objects):
            best_iou, best_gi = 0.0, -1
            for gi, gt in enumerate(gt_objects):
                if gi in matched_gt:
                    continue
                iou = _iou(det, gt)
                if iou > best_iou:
                    best_iou, best_gi = iou, gi

            cls = _label(det)
            self._stats.setdefault(cls, {"tp": 0, "fp": 0, "fn": 0})

            if best_iou >= self._iou_thresh:
                self._stats[cls]["tp"] += 1
                matched_gt.add(best_gi)
                matched_det.add(di)
            else:
                self._stats[cls]["fp"] += 1

        # Unmatched GT → false negatives
        for gi, gt in enumerate(gt_objects):
            if gi not in matched_gt:
                cls = _label(gt)
                self._stats.setdefault(cls, {"tp": 0, "fp": 0, "fn": 0})
                self._stats[cls]["fn"] += 1

    def _publish_metrics(self):
        if not self._stats:
            return

        report = {}
        for cls, s in self._stats.items():
            tp, fp, fn = s["tp"], s["fp"], s["fn"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)
                  if (precision + recall) > 0 else 0.0)
            report[cls] = {
                "precision": round(precision, 3),
                "recall":    round(recall, 3),
                "f1":        round(f1, 3),
                "tp": tp, "fp": fp, "fn": fn,
            }

        msg = String()
        msg.data = json.dumps({"timestamp": time.time(), "classes": report})
        self._pub.publish(msg)
        self.get_logger().info(f"Perception metrics: {report}")


def main():
    rclpy.init()
    node = PerceptionEvalNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
