"""
Convert Autoware rosbag files into an E2E training dataset.

Reads image frames and matching AckermannControlCommand from a .db3 bag
and writes:
  <out_dir>/images/<timestamp>.png
  <out_dir>/labels.csv  (filename, steer, throttle)

Usage:
  python -m e2e_control.bags2dataset \
    --bag /path/to/recording.db3 \
    --out /data/dataset \
    --fps 10
"""

import argparse
import csv
import pathlib
import sqlite3
import struct
import time
from typing import Iterator

import cv2
import numpy as np


# ---- minimal CDR deserializers (no rclpy needed at conversion time) ----

def _read_u32(buf: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from("<I", buf, offset)[0], offset + 4


def _decode_image(data: bytes) -> np.ndarray | None:
    """Decode sensor_msgs/Image CDR payload → BGR ndarray."""
    try:
        offset = 4  # skip CDR header
        # stamp (sec uint32 + nanosec uint32)
        offset += 8
        # frame_id string: length + chars + padding
        str_len, offset = _read_u32(data, offset)
        offset += str_len + (-str_len % 4)
        # height, width
        height, offset = _read_u32(data, offset)
        width,  offset = _read_u32(data, offset)
        # encoding string
        enc_len, offset = _read_u32(data, offset)
        encoding = data[offset:offset + enc_len - 1].decode()
        offset += enc_len + (-enc_len % 4)
        # is_bigendian (uint8) + padding (3) + step (uint32)
        offset += 1 + 3
        step, offset = _read_u32(data, offset)
        # data array
        data_len, offset = _read_u32(data, offset)
        raw = data[offset:offset + data_len]

        arr = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, -1)
        if encoding in ("rgb8", "RGB8"):
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr  # bgr8 already
    except Exception:
        return None


def _decode_ackermann(data: bytes) -> tuple[float, float] | None:
    """Decode AckermannControlCommand CDR → (steer_rad, accel_ms2)."""
    try:
        offset = 4  # CDR header
        # stamp
        offset += 8
        # lateral: stamp(8) + steering_tire_angle(f32) + steering_tire_rotation_rate(f32)
        offset += 8
        steer = struct.unpack_from("<f", data, offset)[0]
        offset += 8
        # longitudinal: stamp(8) + speed(f32) + acceleration(f32) + jerk(f32)
        offset += 8 + 4
        accel = struct.unpack_from("<f", data, offset)[0]
        return steer, accel
    except Exception:
        return None


# ---- rosbag3 reader ----

def _iter_messages(bag_path: pathlib.Path, topics: set[str]) -> Iterator[tuple[str, int, bytes]]:
    """Yield (topic, timestamp_ns, data) from a .db3 bag."""
    conn = sqlite3.connect(str(bag_path))
    topic_ids = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT name, id FROM topics WHERE name IN ({})".format(
                ",".join("?" * len(topics))
            ),
            list(topics),
        )
    }
    id_to_topic = {v: k for k, v in topic_ids.items()}
    if not topic_ids:
        conn.close()
        return
    placeholders = ",".join("?" * len(topic_ids))
    for row in conn.execute(
        f"SELECT topic_id, timestamp, data FROM messages WHERE topic_id IN ({placeholders}) ORDER BY timestamp",
        list(topic_ids.values()),
    ):
        topic_id, ts, data = row
        yield id_to_topic[topic_id], ts, bytes(data)
    conn.close()


# ---- main conversion ----

IMAGE_TOPIC = "/sensing/camera/camera0/image_raw"
CONTROL_TOPIC = "/control/command/control_cmd"
MAX_STEER_RAD = 0.5236
MAX_ACCEL_MS2 = 3.0


def convert(bag_path: pathlib.Path, out_dir: pathlib.Path, target_fps: float):
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    ns_interval = int(1e9 / target_fps)
    last_saved_ns = 0
    last_cmd: tuple[float, float] | None = None
    saved = 0

    with open(out_dir / "labels.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "steer", "throttle"])

        for topic, ts_ns, data in _iter_messages(
            bag_path, {IMAGE_TOPIC, CONTROL_TOPIC}
        ):
            if topic == CONTROL_TOPIC:
                last_cmd = _decode_ackermann(data)

            elif topic == IMAGE_TOPIC and last_cmd is not None:
                if ts_ns - last_saved_ns < ns_interval:
                    continue
                last_saved_ns = ts_ns

                img = _decode_image(data)
                if img is None:
                    continue

                steer_norm  = max(-1.0, min(1.0, last_cmd[0] / MAX_STEER_RAD))
                accel_norm  = max(-1.0, min(1.0, last_cmd[1] / MAX_ACCEL_MS2))

                fname = f"{ts_ns:020d}.png"
                cv2.imwrite(str(img_dir / fname), img)
                writer.writerow([fname, f"{steer_norm:.6f}", f"{accel_norm:.6f}"])
                f.flush()
                saved += 1

                if saved % 50 == 0:
                    print(f"  Saved {saved} frames...")

    print(f"Done. {saved} frames written to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert rosbag to E2E dataset")
    parser.add_argument("--bag",  required=True, help="Path to .db3 bag file")
    parser.add_argument("--out",  required=True, help="Output directory")
    parser.add_argument("--fps",  type=float, default=10.0, help="Target frames per second")
    args = parser.parse_args()
    convert(pathlib.Path(args.bag), pathlib.Path(args.out), args.fps)
