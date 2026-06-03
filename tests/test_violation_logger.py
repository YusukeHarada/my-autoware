"""
Unit tests for ViolationLoggerNode logic.

Tests run the detection methods directly without a live ROS 2 runtime
by instantiating a stripped-down version of the business logic.
"""

import collections
import json
import pathlib
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "apps" / "violation_logger"))


# ---- extract pure logic from node so we can test without rclpy ----

class _ViolationDetector:
    """Pure-Python extraction of ViolationLoggerNode detection logic."""

    def __init__(self, limit_kmh=50.0, brake_thresh=-4.0, steer_thresh=0.5):
        self._limit_ms     = limit_kmh / 3.6
        self._brake_thresh = brake_thresh
        self._steer_thresh = steer_thresh
        self._speed_history: collections.deque = collections.deque(maxlen=10)
        self._steer_history: collections.deque = collections.deque(maxlen=5)
        self.events: list[str] = []

    def on_velocity(self, speed_ms: float, t: float):
        self._speed_history.append((t, speed_ms))
        if speed_ms > self._limit_ms:
            self.events.append("SPEED_VIOLATION")
        if len(self._speed_history) >= 2:
            dt = t - self._speed_history[-2][0]
            if dt > 0:
                accel = (speed_ms - self._speed_history[-2][1]) / dt
                if accel < self._brake_thresh:
                    self.events.append("SUDDEN_BRAKE")

    def on_steering(self, angle: float, t: float):
        self._steer_history.append((t, angle))
        if len(self._steer_history) >= 2:
            dt = t - self._steer_history[-2][0]
            if dt > 0:
                rate = abs(angle - self._steer_history[-2][1]) / dt
                if rate > self._steer_thresh:
                    self.events.append("SHARP_STEER")


# ---- tests ----

def test_no_violations_normal_driving():
    d = _ViolationDetector(limit_kmh=50.0)
    for i in range(10):
        d.on_velocity(10.0, float(i))
    assert d.events == []


def test_speed_violation_detected():
    d = _ViolationDetector(limit_kmh=50.0)
    d.on_velocity(10.0, 0.0)
    d.on_velocity(15.0, 1.0)   # 54 km/h → over limit
    assert "SPEED_VIOLATION" in d.events


def test_speed_exactly_at_limit_no_violation():
    d = _ViolationDetector(limit_kmh=50.0)
    d.on_velocity(50.0 / 3.6, 0.0)   # exactly 50 km/h
    assert "SPEED_VIOLATION" not in d.events


def test_sudden_brake_detected():
    d = _ViolationDetector(brake_thresh=-4.0)
    d.on_velocity(20.0, 0.0)
    d.on_velocity(15.0, 1.0)   # -5 m/s² < -4.0 threshold
    assert "SUDDEN_BRAKE" in d.events


def test_gentle_brake_not_flagged():
    d = _ViolationDetector(brake_thresh=-4.0)
    d.on_velocity(20.0, 0.0)
    d.on_velocity(18.0, 1.0)   # -2 m/s², within comfort zone
    assert "SUDDEN_BRAKE" not in d.events


def test_sharp_steer_detected():
    d = _ViolationDetector(steer_thresh=0.5)
    d.on_steering(0.0,  0.0)
    d.on_steering(0.6,  1.0)   # 0.6 rad/s > 0.5 threshold
    assert "SHARP_STEER" in d.events


def test_gentle_steer_not_flagged():
    d = _ViolationDetector(steer_thresh=0.5)
    d.on_steering(0.0,  0.0)
    d.on_steering(0.2,  1.0)   # 0.2 rad/s ← ok
    assert "SHARP_STEER" not in d.events


def test_multiple_violation_types():
    d = _ViolationDetector()
    d.on_velocity(20.0, 0.0)
    d.on_velocity(15.5, 1.0)   # 55.8 km/h speed violation + -4.5 m/s² brake
    assert "SPEED_VIOLATION" in d.events
    assert "SUDDEN_BRAKE" in d.events
