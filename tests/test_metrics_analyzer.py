"""Tests for metrics_analyzer.analyze (no ROS 2 runtime needed)."""

import json
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "apps" / "metrics_analyzer"))
from metrics_analyzer.analyze import compute_metrics, load_speed_log, load_violations


# ---- fixtures ----

@pytest.fixture
def speed_csv(tmp_path):
    p = tmp_path / "speed_log.csv"
    p.write_text(
        "timestamp,speed_ms,speed_kmh,alert\n"
        "1000.0,10.0,36.0,0\n"
        "1001.0,14.0,50.4,1\n"
        "1002.0,15.0,54.0,1\n"
        "1003.0,8.0,28.8,0\n"
    )
    return p


@pytest.fixture
def violations_json(tmp_path):
    p = tmp_path / "violations.json"
    data = [
        {"timestamp": 1001.0, "type": "SPEED_VIOLATION", "speed_kmh": 50.4, "limit_kmh": 50.0},
        {"timestamp": 1002.0, "type": "SPEED_VIOLATION", "speed_kmh": 54.0, "limit_kmh": 50.0},
        {"timestamp": 1003.0, "type": "SUDDEN_BRAKE",    "decel_ms2": -4.5, "threshold": -4.0},
    ]
    p.write_text(json.dumps(data))
    return p


# ---- tests ----

def test_load_speed_log(speed_csv):
    rows = load_speed_log(speed_csv)
    assert len(rows) == 4
    assert rows[0]["kmh"] == pytest.approx(36.0)
    assert rows[1]["alert"] == 1


def test_load_violations(violations_json):
    viols = load_violations(violations_json)
    assert len(viols) == 3
    assert viols[2]["type"] == "SUDDEN_BRAKE"


def test_compute_metrics_basic(speed_csv, violations_json):
    speeds = load_speed_log(speed_csv)
    viols  = load_violations(violations_json)
    m = compute_metrics(speeds, viols)

    assert m["avg_speed_kmh"] == pytest.approx((36.0 + 50.4 + 54.0 + 28.8) / 4, rel=0.01)
    assert m["max_speed_kmh"] == pytest.approx(54.0)
    assert m["pct_over_limit"] == pytest.approx(50.0)    # 2 of 4 rows
    assert m["total_violations"] == 3
    assert m["violation_types"]["SPEED_VIOLATION"] == 2
    assert m["violation_types"]["SUDDEN_BRAKE"] == 1


def test_comfort_score_deductions(speed_csv, violations_json):
    speeds = load_speed_log(speed_csv)
    viols  = load_violations(violations_json)
    m = compute_metrics(speeds, viols)
    # 2 × SPEED_VIOLATION(2) + 1 × SUDDEN_BRAKE(5) = 9 deductions
    assert m["comfort_score"] == pytest.approx(100.0 - 9, rel=0.01)


def test_empty_inputs():
    m = compute_metrics([], [])
    assert m == {}


def test_no_violations(speed_csv):
    speeds = load_speed_log(speed_csv)
    m = compute_metrics(speeds, [])
    assert m["total_violations"] == 0
    assert m["comfort_score"] == pytest.approx(100.0)


def test_chart_generated(speed_csv, violations_json, tmp_path):
    """Chart file should be written without errors."""
    from metrics_analyzer.analyze import make_charts
    speeds = load_speed_log(speed_csv)
    viols  = load_violations(violations_json)
    m = compute_metrics(speeds, viols)
    chart = tmp_path / "chart.png"
    make_charts(speeds, viols, m, chart)
    assert chart.exists()
    assert chart.stat().st_size > 1000
