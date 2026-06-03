# My Autoware — シミュレーション環境

Tier4 の [Autoware](https://github.com/autowarefoundation/autoware) を Docker で手軽に試せるセットアップです。

---

## システム要件

| 項目 | 最低要件 |
|------|----------|
| OS | Ubuntu 22.04 (Jammy) |
| CPU | 8コア以上 |
| RAM | 16 GB 以上 |
| GPU | NVIDIA RTX 2080 以上（CUDA 12.x） |
| Docker | 24.x 以上 + NVIDIA Container Toolkit |
| ディスク | 50 GB 以上の空き |

---

## クイックスタート

```bash
# 1. セットアップ（初回のみ）
bash scripts/setup.sh

# 2. シミュレーターを選んで起動
bash scripts/planning_simulator.sh   # インタラクティブ計画シミュ
bash scripts/rosbag_replay.sh        # rosbag リプレイ
bash scripts/awsim.sh                # AWSIM デジタルツイン
```

---

## シミュレーションモード一覧

### 1. Planning Simulator（最も手軽）

```
bash scripts/planning_simulator.sh
```

RViz 上でスタート地点とゴール地点を設定すると、Autoware が自動で経路を生成して走行します。
ダミーの車・歩行者を追加して障害物回避や車線変更のテストができます。

**RViz の操作手順:**
1. `2D Pose Estimate` → 地図上で初期位置をクリック＆ドラッグ
2. `2D Nav Goal` → 目的地をクリック＆ドラッグ
3. サイドパネルの `Engage` ボタン → 自動走行開始
4. ツールバーの `2D Dummy Car` → 障害物を追加

---

### 2. Rosbag Replay

```bash
bash scripts/rosbag_replay.sh                        # サンプルbag
bash scripts/rosbag_replay.sh /path/to/your.db3     # 独自bag
```

実際のセンサデータを記録した rosbag を流しながら Sensing / Localization / Perception スタックを検証します。

---

### 3. AWSIM Digital Twin（最もリアル）

```bash
# AWSimバイナリを先にダウンロード
bash scripts/download_awsim.sh

# Terminal 1: Autoware 起動
bash scripts/awsim.sh

# Terminal 2: AWSIM バイナリ起動
./awsim/AWSIM_Labs.x86_64
```

Unity 製の高精度シミュレーターと Autoware を連携させたリアルタイムデジタルツインです。
LiDAR・カメラ・IMU のセンサ出力を Unity 側でシミュレートします。

---

### 4. Scenario Simulator（自動テスト）

```bash
docker compose run --rm scenario_simulator
```

OpenSCENARIO 形式のシナリオを headless 実行して回帰テストに使えます。
シナリオファイルは `config/scenarios/` に置いてください。

---

## 作れるサンプルアプリ

### A. 自律走行デモ（Planning Simulator ベース）
- 指定ルートの自動走行
- 障害物検知 → 停止・回避
- 車線変更・交差点通過

### B. 交通違反検知ロガー（Rosbag ベース）
- rosbag を流して信号無視・速度超過を検出するノードを実装
- ROS 2 トピックを subscribe して CSV にロギング

```python
# 例: 速度監視ノード
import rclpy
from autoware_auto_vehicle_msgs.msg import VelocityReport

def velocity_callback(msg):
    if msg.longitudinal_velocity > 13.9:  # 50 km/h
        print(f"[ALERT] Speed limit exceeded: {msg.longitudinal_velocity:.1f} m/s")
```

### C. 経路可視化ダッシュボード（Web UI）
- Autoware の `/planning/trajectory` トピックを rosbridge 経由で取得
- React + Leaflet でブラウザに地図表示

### D. シナリオ自動テスト CI
- GitHub Actions で `scenario_simulator` コンテナを起動
- 追越し・緊急停止などのシナリオを自動実行して合否判定

### E. End-to-End AI 制御（研究向け）
- AWSIM + Autoware の画像データでニューラルネットワークを学習
- `autoware_auto_control_msgs` の制御指令を AI で出力

---

## ディレクトリ構成

```
my-autoware/
├── docker-compose.yaml          # 4つのシミュレーションサービス定義
├── scripts/
│   ├── setup.sh                 # 初期セットアップ（イメージ取得・マップDL）
│   ├── planning_simulator.sh    # Planning Simulator 起動
│   ├── rosbag_replay.sh         # Rosbag リプレイ起動
│   ├── awsim.sh                 # AWSIM モード起動
│   └── download_awsim.sh        # AWSIM バイナリ・マップDL
├── config/
│   └── scenarios/
│       └── sample.yaml          # サンプルシナリオ定義
├── maps/                        # 地図・rosbag 置き場（gitignore済み）
└── README.md
```

---

## 参考リンク

- [Autoware Documentation](https://autowarefoundation.github.io/autoware-documentation/main/)
- [AWSIM Labs](https://github.com/autowarefoundation/AWSIM-Labs)
- [Autoware Docker イメージ](https://hub.docker.com/r/autoware/autoware)
- [Tier4 公式サイト](https://tier4.jp/en/)
