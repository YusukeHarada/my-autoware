# Autoware simulation environment — convenience targets.
# Run any target with: make <target>

.PHONY: help setup build test sim-planning sim-rosbag sim-awsim sim-full \
        scenarios dashboard metrics clean

SHELL := /bin/bash
BAG_FILE ?= maps/rosbag/sample.db3
SIM_MODE ?= planning

help:
	@echo ""
	@echo "  Autoware Simulation Makefile"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make setup          First-time setup (pull image, download maps)"
	@echo "  make build          Build all custom ROS 2 packages"
	@echo "  make test           Run unit tests (pytest)"
	@echo ""
	@echo "  make sim-planning   Launch Planning Simulator (interactive)"
	@echo "  make sim-rosbag     Replay rosbag through Autoware"
	@echo "  make sim-awsim      Connect to AWSIM digital twin"
	@echo "  make sim-full       Full stack: Autoware + all monitors + dashboard"
	@echo ""
	@echo "  make scenarios      Run all scenario tests and generate HTML report"
	@echo "  make dashboard      Start web dashboard only"
	@echo "  make metrics        Analyze latest logs and generate chart"
	@echo "  make clean          Remove generated results"
	@echo ""
	@echo "  Variables:"
	@echo "    BAG_FILE=<path>   Bag file for sim-rosbag (default: $(BAG_FILE))"
	@echo "    SIM_MODE=<mode>   Mode for sim-full: planning|rosbag|awsim"
	@echo ""

setup:
	bash scripts/setup.sh

build:
	bash scripts/build_apps.sh

test:
	@pip install pytest matplotlib --quiet
	pytest tests/ -v

sim-planning:
	bash scripts/planning_simulator.sh

sim-rosbag:
	bash scripts/rosbag_replay.sh $(BAG_FILE)

sim-awsim:
	bash scripts/awsim.sh

sim-full:
	xhost +local:docker 2>/dev/null || true
	SIM_MODE=$(SIM_MODE) BAG_FILE=$(BAG_FILE) \
	  docker compose -f docker-compose.full.yaml up

scenarios:
	bash scripts/run_scenarios.sh --out results/scenarios

dashboard:
	xhost +local:docker 2>/dev/null || true
	docker compose -f apps/web_dashboard/docker-compose.yaml up

metrics:
	@mkdir -p results/metrics
	python -m metrics_analyzer.analyze \
	  --speed-log  results/speed_log.csv \
	  --violations results/violations.json \
	  --out        results/metrics 2>/dev/null || \
	  echo "[WARN] Log files not found. Run a simulation first."

clean:
	rm -rf results/
	docker compose -f docker-compose.full.yaml down -v 2>/dev/null || true
