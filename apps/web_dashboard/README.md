# Web Dashboard — Autoware リアルタイム可視化

RViz なしでブラウザから Autoware の状態をリアルタイム監視できるダッシュボードです。

## 構成

```
web_dashboard/
├── backend/   FastAPI + ROS 2 bridge (WebSocket / REST)
└── frontend/  HTML + Leaflet マップ (依存関係なし)
```

## 起動

```bash
cd apps/web_dashboard
docker compose up
```

ブラウザで `http://localhost:3000` を開く。

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/status` | 最新の車両状態（速度・位置・ヘディング） |
| GET | `/trajectory` | 計画経路（GeoJSON LineString） |
| WS  | `/ws` | 車両状態のリアルタイムストリーム |
| GET | `/health` | ヘルスチェック |

## 表示内容

- 車速（速度超過で色変化: 緑 → 黄 → 赤）
- 地図座標 (X, Y) とヘディング角
- 計画経路の地図オーバーレイ
- 速度超過アラート
