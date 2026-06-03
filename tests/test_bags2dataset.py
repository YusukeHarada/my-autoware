"""Tests for e2e_control.bags2dataset (SQLite simulation, no real bag needed)."""

import pathlib
import sqlite3
import struct
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "apps" / "e2e_control"))
from e2e_control.bags2dataset import _decode_ackermann, _read_u32, convert


# ---- unit tests for CDR helpers ----

def test_read_u32():
    buf = struct.pack("<II", 42, 99)
    val, offset = _read_u32(buf, 0)
    assert val == 42
    assert offset == 4
    val2, offset2 = _read_u32(buf, 4)
    assert val2 == 99


def test_decode_ackermann_roundtrip():
    """Build a minimal CDR buffer and verify round-trip decoding."""
    steer_expected = 0.25
    accel_expected = 1.5

    # CDR header (4 bytes) + stamp (8) + lateral stamp (8) + steer (f32) + steer_rate (f32)
    # + longitudinal stamp (8) + speed (f32) + accel (f32)
    buf = bytearray(4 + 8 + 8 + 4 + 4 + 8 + 4 + 4)
    struct.pack_into("<f", buf, 4 + 8 + 8,           steer_expected)
    struct.pack_into("<f", buf, 4 + 8 + 8 + 4 + 4 + 8 + 4, accel_expected)

    result = _decode_ackermann(bytes(buf))
    assert result is not None
    steer, accel = result
    assert steer == pytest.approx(steer_expected, rel=1e-5)
    assert accel == pytest.approx(accel_expected, rel=1e-5)


def test_decode_ackermann_bad_data():
    """Truncated buffer should return None, not raise."""
    assert _decode_ackermann(b"\x00\x01\x02") is None


# ---- integration: convert against a minimal synthetic bag ----

def _make_synthetic_bag(path: pathlib.Path):
    """Create a minimal rosbag3 SQLite DB with fake messages."""
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE topics (
            id   INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            serialization_format TEXT,
            offered_qos_profiles TEXT
        );
        CREATE TABLE messages (
            id       INTEGER PRIMARY KEY,
            topic_id INTEGER,
            timestamp INTEGER,
            data     BLOB
        );
    """)
    # Register topics
    conn.execute(
        "INSERT INTO topics VALUES (1, '/sensing/camera/camera0/image_raw', "
        "'sensor_msgs/msg/Image', 'cdr', '')"
    )
    conn.execute(
        "INSERT INTO topics VALUES (2, '/control/command/control_cmd', "
        "'autoware_auto_control_msgs/msg/AckermannControlCommand', 'cdr', '')"
    )

    # Insert a control message (steer=0.1, accel=2.0)
    ctrl_buf = bytearray(4 + 8 + 8 + 4 + 4 + 8 + 4 + 4)
    struct.pack_into("<f", ctrl_buf, 4 + 8 + 8,                   0.1)
    struct.pack_into("<f", ctrl_buf, 4 + 8 + 8 + 4 + 4 + 8 + 4,  2.0)
    conn.execute(
        "INSERT INTO messages VALUES (1, 2, 1000000000, ?)",
        (bytes(ctrl_buf),),
    )

    # Insert a fake image message that will decode to None (truncated) —
    # convert() should skip it gracefully rather than crash
    conn.execute(
        "INSERT INTO messages VALUES (2, 1, 1100000000, ?)",
        (b"\x00" * 16,),
    )
    conn.commit()
    conn.close()


def test_convert_skips_bad_image(tmp_path):
    bag = tmp_path / "test.db3"
    _make_synthetic_bag(bag)
    out = tmp_path / "dataset"
    # Should complete without raising even with a bad image payload
    convert(bag, out, target_fps=10.0)
    # Zero valid frames written (image was truncated)
    assert not any((out / "images").glob("*.png")) if (out / "images").exists() else True
