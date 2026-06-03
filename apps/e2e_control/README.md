# E2E Control — カメラ画像からの自律走行

MobileNetV3 をベースにしたニューラルネットワークが前方カメラ画像から直接ステアリング・アクセルを制御します。Autoware の Planning/Control スタックを置き換える研究向けノードです。

## ワークフロー

```
AWSIM走行 → データ収集 → 学習 → AWSIM で推論実行
```

## 1. データ収集

AWSIM + Autoware (通常モード) を走行させながら収集：

```bash
ros2 run e2e_control e2e_collect --ros-args -p out_dir:=/data/dataset
```

`/data/dataset/images/` に PNG、`labels.csv` に steer/throttle が記録されます。

## 2. 学習

```bash
python -m e2e_control.train \
  --data-dir /data/dataset \
  --out weights/e2e_driver.pt \
  --epochs 30
```

GPU があれば自動で CUDA を使用します。

## 3. 推論（AWSIM 接続時）

```bash
ros2 run e2e_control e2e_control \
  --ros-args \
  -p model_path:=weights/e2e_driver.pt \
  -p target_speed_kmh:=30.0
```

## モデルアーキテクチャ

```
入力: カメラ画像 (224×224 RGB)
  ↓
MobileNetV3-Small (ImageNet pretrained backbone)
  ↓
Linear(576→128) → Hardswish → Dropout(0.2)
  ↓
Linear(128→2) → Tanh
  ↓
出力: [steer (-1〜1), throttle (-1〜1)]
```

## トピック

| 方向 | トピック | 型 |
|------|----------|----|
| Subscribe | `/sensing/camera/camera0/image_raw` | `sensor_msgs/Image` |
| Publish | `/control/command/control_cmd` | `autoware_auto_control_msgs/AckermannControlCommand` |
