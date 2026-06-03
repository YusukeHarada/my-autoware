"""Tests for perception_eval IoU/matching logic (no ROS 2 needed)."""

import pathlib
import sys
import types

import pytest

# Stub out ROS 2 modules so we can import the node without a live install
def _stub(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

rclpy_mod      = _stub("rclpy")
rclpy_mod.init = lambda: None
rclpy_node     = _stub("rclpy.node")
rclpy_node.Node = object

_stub("std_msgs")
std_msgs_msg = _stub("std_msgs.msg")
std_msgs_msg.String = object

_stub("autoware_auto_perception_msgs")
ap_msg = _stub("autoware_auto_perception_msgs.msg")
ap_msg.DetectedObjects = object

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "apps" / "perception_eval"))
from perception_eval.node import _iou, _aabb, _label


# ---- tiny stub object ----

def _make_obj(cx, cy, w, l, label_int=1):
    """Build a minimal stub that matches the field access in _aabb / _label."""
    import types

    obj = types.SimpleNamespace()

    pos = types.SimpleNamespace(x=cx, y=cy, z=0.0)
    pose = types.SimpleNamespace(position=pos, orientation=None)
    pose_cov = types.SimpleNamespace(pose=pose)
    kin = types.SimpleNamespace(pose_with_covariance=pose_cov)

    shape = types.SimpleNamespace(dimensions=types.SimpleNamespace(x=w, y=l, z=1.8))

    cls_entry = types.SimpleNamespace(label=label_int)

    obj.kinematics    = kin
    obj.shape         = shape
    obj.classification = [cls_entry]
    return obj


# ---- tests ----

def test_iou_perfect_overlap():
    a = _make_obj(0.0, 0.0, 2.0, 4.0)
    assert _iou(a, a) == pytest.approx(1.0)


def test_iou_no_overlap():
    a = _make_obj(0.0, 0.0, 2.0, 2.0)
    b = _make_obj(10.0, 10.0, 2.0, 2.0)
    assert _iou(a, b) == pytest.approx(0.0)


def test_iou_partial_overlap():
    # a: x [0,2], y [0,2]   b: x [1,3], y [0,2]
    # intersection: [1,2]×[0,2] = 1×2 = 2
    # union: 4 + 4 - 2 = 6
    a = _make_obj(1.0, 1.0, 2.0, 2.0)
    b = _make_obj(2.0, 1.0, 2.0, 2.0)
    assert _iou(a, b) == pytest.approx(2.0 / 6.0, rel=0.01)


def test_iou_symmetry():
    a = _make_obj(0.0, 0.0, 3.0, 2.0)
    b = _make_obj(1.0, 0.5, 2.0, 3.0)
    assert _iou(a, b) == pytest.approx(_iou(b, a))


def test_label_car():
    obj = _make_obj(0, 0, 1, 1, label_int=1)
    assert _label(obj) == "CAR"


def test_label_pedestrian():
    obj = _make_obj(0, 0, 1, 1, label_int=6)
    assert _label(obj) == "PEDESTRIAN"


def test_label_unknown():
    obj = _make_obj(0, 0, 1, 1, label_int=99)
    assert _label(obj) == "UNKNOWN"


def test_label_empty_classification():
    obj = _make_obj(0, 0, 1, 1)
    obj.classification = []
    assert _label(obj) == "UNKNOWN"
