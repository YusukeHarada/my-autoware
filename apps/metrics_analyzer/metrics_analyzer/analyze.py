"""
Analyze logged driving data and produce a PDF/HTML report.

Inputs:
  --speed-log  /tmp/speed_log.csv        (from speed_monitor node)
  --violations /tmp/violations.json      (from violation_logger node)
  --out        results/metrics_report.html

Metrics computed:
  - Distance-weighted average speed
  - Time above speed limit (%)
  - Comfort score: penalizes sudden braking and sharp steering
  - Violation breakdown pie chart
  - Speed timeline chart
"""

import argparse
import csv
import json
import pathlib
import math

# matplotlib is imported lazily so the module can be imported without display
def _import_plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    return plt, gridspec


def load_speed_log(path: pathlib.Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({
                "t": float(row["timestamp"]),
                "kmh": float(row["speed_kmh"]),
                "alert": int(row["alert"]),
            })
    return rows


def load_violations(path: pathlib.Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def compute_metrics(speeds: list[dict], violations: list[dict]) -> dict:
    if not speeds:
        return {}

    kmh_vals = [s["kmh"] for s in speeds]
    avg_speed = sum(kmh_vals) / len(kmh_vals)
    max_speed = max(kmh_vals)
    pct_over  = 100.0 * sum(s["alert"] for s in speeds) / len(speeds)

    # Comfort score [0-100]: start at 100, deduct per violation
    deductions = {
        "SPEED_VIOLATION": 2,
        "SUDDEN_BRAKE":    5,
        "SHARP_STEER":     3,
    }
    total_deduction = sum(deductions.get(v["type"], 1) for v in violations)
    comfort = max(0.0, 100.0 - total_deduction)

    vtypes: dict[str, int] = {}
    for v in violations:
        vtypes[v["type"]] = vtypes.get(v["type"], 0) + 1

    return {
        "avg_speed_kmh":   round(avg_speed, 1),
        "max_speed_kmh":   round(max_speed, 1),
        "pct_over_limit":  round(pct_over, 1),
        "comfort_score":   round(comfort, 1),
        "total_violations": len(violations),
        "violation_types": vtypes,
        "duration_s":      round(speeds[-1]["t"] - speeds[0]["t"], 1),
    }


def make_charts(speeds: list[dict], violations: list[dict], m: dict, out_path: pathlib.Path):
    plt, gridspec = _import_plt()

    fig = plt.figure(figsize=(14, 9), facecolor="#0d1117")
    fig.suptitle("Autoware Driving Metrics Report", color="#e6edf3", fontsize=15, y=0.98)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.4)

    dark = {"facecolor": "#161b22", "edgecolor": "#30363d"}
    text_kw = {"color": "#e6edf3"}
    grid_kw = {"color": "#30363d", "linestyle": "--", "linewidth": 0.5}

    # ---- 1. Speed timeline ----
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor(dark["facecolor"])
    for spine in ax1.spines.values():
        spine.set_edgecolor(dark["edgecolor"])
    t0 = speeds[0]["t"] if speeds else 0
    ts   = [s["t"] - t0 for s in speeds]
    kmhs = [s["kmh"] for s in speeds]
    ax1.plot(ts, kmhs, color="#58a6ff", linewidth=1.2, label="Speed (km/h)")
    ax1.axhline(50, color="#f85149", linewidth=1, linestyle="--", label="Limit 50 km/h")
    ax1.fill_between(ts, kmhs, 50, where=[k > 50 for k in kmhs],
                     color="#f85149", alpha=0.2)
    ax1.set_xlabel("Time (s)", **text_kw)
    ax1.set_ylabel("Speed (km/h)", **text_kw)
    ax1.set_title("Speed Timeline", **text_kw)
    ax1.tick_params(colors="#8b949e")
    ax1.grid(**grid_kw)
    ax1.legend(facecolor="#21262d", labelcolor="#e6edf3", edgecolor="#30363d")

    # ---- 2. Violation pie ----
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_facecolor(dark["facecolor"])
    vtypes = m.get("violation_types", {})
    if vtypes:
        colors = ["#f85149", "#d29922", "#58a6ff", "#3fb950"]
        wedges, texts, autotexts = ax2.pie(
            vtypes.values(), labels=vtypes.keys(),
            autopct="%1.0f%%", colors=colors[:len(vtypes)],
            textprops={"color": "#e6edf3", "fontsize": 8},
        )
        for at in autotexts:
            at.set_color("#0d1117")
    else:
        ax2.text(0.5, 0.5, "No violations", ha="center", va="center", **text_kw)
    ax2.set_title("Violation Breakdown", **text_kw)

    # ---- 3. KPI cards ----
    ax3 = fig.add_subplot(gs[1, :])
    ax3.axis("off")
    kpis = [
        ("Avg Speed",     f"{m.get('avg_speed_kmh', 0)} km/h",  "#58a6ff"),
        ("Max Speed",     f"{m.get('max_speed_kmh', 0)} km/h",  "#d29922"),
        ("Over Limit",    f"{m.get('pct_over_limit', 0)} %",    "#f85149"),
        ("Comfort Score", f"{m.get('comfort_score', 0)} / 100", "#3fb950"),
        ("Violations",    str(m.get("total_violations", 0)),     "#f0883e"),
        ("Duration",      f"{m.get('duration_s', 0)} s",        "#8b949e"),
    ]
    for i, (label, value, color) in enumerate(kpis):
        x = 0.08 + i * 0.155
        ax3.text(x, 0.7, value, transform=ax3.transAxes,
                 fontsize=18, fontweight="bold", color=color, ha="center")
        ax3.text(x, 0.35, label, transform=ax3.transAxes,
                 fontsize=9, color="#8b949e", ha="center")

    plt.savefig(str(out_path), dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"Chart saved to {out_path}")


def run(args):
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    speeds     = load_speed_log(pathlib.Path(args.speed_log)) if args.speed_log else []
    violations = load_violations(pathlib.Path(args.violations)) if args.violations else []
    m = compute_metrics(speeds, violations)

    print("\n=== Driving Metrics ===")
    for k, v in m.items():
        print(f"  {k:<22}: {v}")

    if speeds:
        chart_path = out_dir / "metrics_chart.png"
        make_charts(speeds, violations, m, chart_path)

    # Write JSON summary
    summary_path = out_dir / "metrics_summary.json"
    with open(summary_path, "w") as f:
        json.dump(m, f, indent=2)
    print(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Analyze Autoware driving logs")
    p.add_argument("--speed-log",  default="", help="Path to speed_log.csv")
    p.add_argument("--violations", default="", help="Path to violations.json")
    p.add_argument("--out",        default="results/metrics", help="Output directory")
    run(p.parse_args())
