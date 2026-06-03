# Speed Monitor — ROS 2 ノード

Autoware の車速トピックを監視し、制限速度超過をアラートとして Publish し CSV にロギングします。

## ビルド

```bash
cd apps/speed_monitor
colcon build --packages-select speed_monitor
source install/setup.bash
```

## 実行

```bash
# デフォルト（50 km/h 制限、ログは /tmp/speed_log.csv）
ros2 run speed_monitor speed_monitor

# カスタム設定
ros2 run speed_monitor speed_monitor \
  --ros-args \
  -p speed_limit_kmh:=30.0 \
  -p log_path:=/home/user/speed_log.csv
```

## トピック

| 方向 | トピック | 型 |
|------|----------|----|
| Subscribe | `/vehicle/status/velocity_status` | `autoware_auto_vehicle_msgs/VelocityReport` |
| Publish | `/speed_monitor/alert` | `std_msgs/String` |

## アラート受信

```bash
ros2 topic echo /speed_monitor/alert
```
