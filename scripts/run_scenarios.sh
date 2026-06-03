#!/usr/bin/env bash
# Run all scenario YAML files and generate an HTML test report.
#
# Usage: bash scripts/run_scenarios.sh [--out results/]

set -euo pipefail

SCENARIO_DIR="$(pwd)/config/scenarios"
OUT_DIR="$(pwd)/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

while [[ $# -gt 0 ]]; do
    case $1 in
        --out) OUT_DIR="$2"; shift 2 ;;
        *)     echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUT_DIR"

RESULTS=()   # array of "name|status|duration"

run_scenario() {
    local yaml_file="$1"
    local name
    name=$(basename "$yaml_file" .yaml)
    local start end duration
    start=$(date +%s)

    echo "[RUN] $name ..."

    set +e
    docker compose run --rm scenario_simulator \
        bash -c "
          source /opt/autoware/setup.bash &&
          ros2 launch scenario_test_runner scenario_test_runner.launch.py
            architecture_type:=awf/universe/20240605
            record:=false
            scenario:=/autoware_config/scenarios/$(basename "$yaml_file")
            sensor_model:=sample_sensor_kit
            vehicle_model:=sample_vehicle
        " > "$OUT_DIR/${name}.log" 2>&1
    local exit_code=$?
    set -e

    end=$(date +%s)
    duration=$((end - start))

    if [[ $exit_code -eq 0 ]]; then
        local status="PASS"
        echo "  [PASS] ${name} (${duration}s)"
    else
        local status="FAIL"
        echo "  [FAIL] ${name} (${duration}s) — see $OUT_DIR/${name}.log"
    fi

    RESULTS+=("${name}|${status}|${duration}")
}

# ---- run all scenarios ----
for yaml in "$SCENARIO_DIR"/*.yaml; do
    run_scenario "$yaml"
done

# ---- generate HTML report ----
REPORT="$OUT_DIR/report_${TIMESTAMP}.html"
PASS_COUNT=0
FAIL_COUNT=0
for r in "${RESULTS[@]}"; do
    [[ "${r#*|}" == PASS* ]] && ((PASS_COUNT++)) || ((FAIL_COUNT++))
done
TOTAL=$((PASS_COUNT + FAIL_COUNT))

cat > "$REPORT" <<HTML
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>Autoware Scenario Report — ${TIMESTAMP}</title>
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; padding: 32px; }
  h1   { color: #58a6ff; }
  .summary { display: flex; gap: 24px; margin: 24px 0; }
  .badge { padding: 12px 24px; border-radius: 8px; font-size: 1.4rem; font-weight: 700; }
  .pass { background: #1a3a1a; color: #3fb950; }
  .fail { background: #3a1a1a; color: #f85149; }
  .total { background: #1a2a3a; color: #58a6ff; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 10px 16px; text-align: left; border-bottom: 1px solid #30363d; }
  th { background: #161b22; color: #8b949e; font-size: 0.8rem; text-transform: uppercase; }
  tr:hover { background: #161b22; }
  .p { color: #3fb950; font-weight: 700; }
  .f { color: #f85149; font-weight: 700; }
  a { color: #58a6ff; }
</style>
</head>
<body>
<h1>Autoware Scenario Test Report</h1>
<p style="color:#8b949e">Generated: $(date)</p>

<div class="summary">
  <div class="badge total">Total: ${TOTAL}</div>
  <div class="badge pass">PASS: ${PASS_COUNT}</div>
  <div class="badge fail">FAIL: ${FAIL_COUNT}</div>
</div>

<table>
  <thead><tr><th>Scenario</th><th>Result</th><th>Duration (s)</th><th>Log</th></tr></thead>
  <tbody>
HTML

for r in "${RESULTS[@]}"; do
    IFS='|' read -r name status duration <<< "$r"
    css_class=$([[ "$status" == "PASS" ]] && echo "p" || echo "f")
    cat >> "$REPORT" <<ROW
    <tr>
      <td>${name}</td>
      <td class="${css_class}">${status}</td>
      <td>${duration}</td>
      <td><a href="${name}.log">log</a></td>
    </tr>
ROW
done

cat >> "$REPORT" <<HTML
  </tbody>
</table>
</body>
</html>
HTML

echo ""
echo "=== Done: ${PASS_COUNT}/${TOTAL} passed ==="
echo "Report: $REPORT"

# Exit 1 if any failures (useful for CI)
[[ $FAIL_COUNT -eq 0 ]]
