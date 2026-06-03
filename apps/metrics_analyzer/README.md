# Metrics Analyzer — 走行品質レポート

`speed_monitor` と `violation_logger` の出力ログを読み込み、走行品質スコアとグラフを生成します。

## 実行

```bash
python -m metrics_analyzer.analyze \
  --speed-log  /tmp/speed_log.csv \
  --violations /tmp/violations.json \
  --out        results/metrics
```

## 出力

| ファイル | 内容 |
|---------|------|
| `metrics_summary.json` | KPI サマリー（平均速度・超過率・コンフォートスコアなど） |
| `metrics_chart.png`    | 速度タイムライン＋違反内訳グラフ |

## 出力例

```json
{
  "avg_speed_kmh": 32.4,
  "max_speed_kmh": 57.1,
  "pct_over_limit": 3.2,
  "comfort_score": 84.0,
  "total_violations": 8,
  "violation_types": {
    "SPEED_VIOLATION": 5,
    "SUDDEN_BRAKE": 2,
    "SHARP_STEER": 1
  },
  "duration_s": 120.5
}
```

## コンフォートスコアの計算

100点からスタートし、以下を差し引き：

| 違反タイプ | 減点 |
|-----------|------|
| 速度超過 (1回) | -2 |
| 急ブレーキ (1回) | -5 |
| 急ハンドル (1回) | -3 |
