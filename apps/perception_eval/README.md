# Perception Evaluator — AWSIM Ground Truth との照合

AWSIM が提供するグラウンドトゥルース（GT）物体情報と Autoware の検出結果を IoU マッチングで照合し、クラスごとの Precision / Recall / F1 をリアルタイムで計算します。

## 実行（AWSIM 接続時）

```bash
ros2 run perception_eval perception_eval \
  --ros-args \
  -p iou_threshold:=0.3 \
  -p report_interval_s:=5.0
```

## トピック

| 方向 | トピック | 型 |
|------|----------|----|
| Subscribe | `/perception/object_recognition/detection/objects` | `DetectedObjects` |
| Subscribe | `/awsim/ground_truth/objects` | `DetectedObjects` |
| Publish   | `/perception_eval/metrics` | `std_msgs/String` (JSON) |

## 出力例

```json
{
  "timestamp": 1717123456.789,
  "classes": {
    "CAR": {
      "precision": 0.923,
      "recall": 0.875,
      "f1": 0.898,
      "tp": 21, "fp": 2, "fn": 3
    },
    "PEDESTRIAN": {
      "precision": 0.800,
      "recall": 0.667,
      "f1": 0.727,
      "tp": 4, "fp": 1, "fn": 2
    }
  }
}
```

## アルゴリズム

1. 検出物体ごとに全 GT 物体との 2D-AABB IoU を計算
2. IoU ≥ threshold の最大マッチを TP とする
3. マッチしない検出 → FP、マッチしない GT → FN
4. クラス別に集計し `report_interval_s` 秒ごとに Publish
