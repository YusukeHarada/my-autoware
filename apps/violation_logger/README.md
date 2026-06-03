# Violation Logger — 交通違反検知

走行中の以下の違反をリアルタイム検知・記録します。

| 違反タイプ | 検知条件 |
|-----------|---------|
| `SPEED_VIOLATION` | 速度が制限値を超過 |
| `SUDDEN_BRAKE`    | 減速度が閾値を超過（急ブレーキ） |
| `SHARP_STEER`     | ステア角速度が閾値を超過（急ハンドル） |

## 実行

```bash
ros2 run violation_logger violation_logger \
  --ros-args \
  -p speed_limit_kmh:=50.0 \
  -p brake_threshold_ms2:=-4.0 \
  -p steer_rate_threshold:=0.5 \
  -p log_path:=/tmp/violations.json
```

## 出力サンプル (`violations.json`)

```json
[
  { "timestamp": 1717123456.789, "type": "SPEED_VIOLATION",
    "speed_kmh": 53.2, "limit_kmh": 50.0 },
  { "timestamp": 1717123460.012, "type": "SUDDEN_BRAKE",
    "decel_ms2": -4.8, "threshold": -4.0 }
]
```

## トピック

| 方向 | トピック | 型 |
|------|----------|----|
| Subscribe | `/vehicle/status/velocity_status` | `autoware_auto_vehicle_msgs/VelocityReport` |
| Subscribe | `/vehicle/status/steering_status` | `autoware_auto_vehicle_msgs/SteeringReport` |
| Publish   | `/violations` | `std_msgs/String` (JSON) |
