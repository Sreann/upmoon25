# upmoon25-auto Makefile

JETSON_HOST ?= upmoon25@100.97.14.103
JETSON_DIR ?= ~/ros2/upmoon25-auto
RSYNC_SSH_OPTS ?= -o StrictHostKeyChecking=no
RSYNC_EXCLUDES = \
	--exclude '.git/' \
	--exclude '.lunar/' \
	--exclude '.venv-dashboard/' \
	--exclude '__pycache__/' \
	--exclude '*.pyc' \
	--exclude '/build/' \
	--exclude '/install/' \
	--exclude '/log/' \
	--exclude '.ruff_cache/' \
	--exclude 'lunar/.venv/'
DEPLOY_PATHS = \
	BUILD.bash \
	Dockerfile \
	INSTALL.bash \
	MAX_RUN.sh \
	Makefile \
	README.md \
	RUN_LAPTOP_RC.bash \
	RUN_ROBOT.bash \
	docker-compose.yml \
	docs \
	firmware \
	gz_worlds \
	lunar \
	src

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
input ?= field_photos/in
output ?= field_photos/out

.PHONY: build up down restart shell sim dashboard mission-bridge mission-control mission-control-build autonomy-stack lint test test-offline ci tune-flags run kill logs check monitor keyboard config shell-env ros-shell install deploy deploy-dry-run help

help:
	@echo "upmoon25-auto Docker Management"
	@echo ""
	@echo "Usage:"
	@echo "  make build    - Build/Rebuild the Docker image"
	@echo "  make up       - Start the container in background"
	@echo "  make down     - Stop and remove the container"
	@echo "  make restart  - Restart the container"
	@echo "  make shell    - Enter the container's shell"
	@echo "  make sim world=gz_worlds/basic.world - Start simulation"
	@echo "  make dashboard - Launch React mission-control in the container (default port 8501)"
	@echo "  make tune-flags input=... output=... - Batch flag detection on images (no ROS; defaults field_photos/in out)"
	@echo "  make mission-bridge - Launch the safe-command mission-control ROS bridge"
	@echo "  make mission-control - Launch the new web mission-control app"
	@echo "  make mission-control-build - Build the new web mission-control app"
	@echo "  make autonomy-stack grid=[coarse|standard|fine] - Launch shadow-mode perception/autonomy nodes"
	@echo "  make lint       - ty check + ruff + mission-control eslint"
	@echo "  make test       - lint + all offline Python unit tests"
	@echo "  make test-offline - Run hardware-free backend/bridge unit tests only"
	@echo "  make ci         - lint + mission-control production build + offline tests (no Jetson)"
	@echo "  make run profile=[robot|rc|autonomy] - Run specialized profile"
	@echo "  make kill     - Stop all simulation and ROS processes"
	@echo "  make logs     - View logs"
	@echo "  make check    - Unified health audit"
	@echo "  make monitor  - Live error stream"
	@echo "  make keyboard - Control robot via terminal keyboard"
	@echo "  make config   - Show current configuration"
	@echo "  make shell-env - Print export commands for ROS shell setup"
	@echo "  make ros-shell - Open an interactive shell with ROS env loaded"
	@echo "  make install  - Install the lunar CLI (inside container)"
	@echo "  make deploy   - Rsync source tree to the Jetson workspace"
	@echo "  make deploy-dry-run - Preview Jetson rsync changes"

build:
	docker compose build

up:
	docker compose up -d

install:
	docker exec -it upmoon25_ros pip3 install -e ./lunar

down:
	docker compose down

restart:
	docker compose restart

shell:
	docker exec -it upmoon25_ros bash

sim:
	docker exec -it upmoon25_ros lunar sim --world $(world) --headless

dashboard:
	docker exec -it upmoon25_ros lunar dashboard

mission-bridge:
	docker exec -it upmoon25_ros lunar mission-bridge --foreground

mission-control:
	cd lunar/mission-control && pnpm dev --host 0.0.0.0 --port 8501

mission-control-build:
	cd lunar/mission-control && pnpm build

autonomy-stack:
	docker exec -it upmoon25_ros lunar autonomy-stack --grid-preset $(or $(grid),standard)

lint:
	@if [ -x "$(ROOT)/lunar/.venv/bin/python" ]; then \
		cd "$(ROOT)" && uvx ty check src/backend lunar/src --python "$(ROOT)/lunar/.venv/bin/python"; \
	else \
		cd "$(ROOT)" && uvx ty check src/backend lunar/src; \
	fi
	cd "$(ROOT)" && uvx ruff check src/backend lunar/src
	cd "$(ROOT)/lunar/mission-control" && pnpm lint

test: lint
	cd $(ROOT)/lunar && uv run python ../src/backend/test/run_offline_unit_tests.py

test-offline:
	cd $(ROOT)/lunar && uv run python ../src/backend/test/run_offline_unit_tests.py

ci: lint
	cd "$(ROOT)/lunar/mission-control" && pnpm build
	cd "$(ROOT)/lunar" && uv run python ../src/backend/test/run_offline_unit_tests.py

tune-flags:
	@mkdir -p "$(ROOT)/$(output)"
	cd "$(ROOT)" && PYTHONPATH="$(ROOT)/src/backend" uv run --project lunar python "$(ROOT)/src/backend/scripts/tune_flags_on_images.py" --input "$(ROOT)/$(input)" --output "$(ROOT)/$(output)"

run:
	docker exec -it upmoon25_ros lunar run $(profile)

kill:
	docker exec -it upmoon25_ros lunar kill

logs:
	docker exec -it upmoon25_ros lunar logs

check:
	docker exec -it upmoon25_ros lunar check

monitor:
	docker exec -it upmoon25_ros lunar check --live

keyboard:
	docker exec -it upmoon25_ros lunar keyboard

config:
	docker exec -it upmoon25_ros lunar config

shell-env:
	@cd lunar && uv run --no-sync lunar shell-env

ros-shell:
	@bash -lc 'cd lunar && eval "$$(uv run --no-sync lunar shell-env)" && (ros2 daemon stop >/dev/null 2>&1 || true) && (ros2 daemon start >/dev/null 2>&1 || true) && export PS1="(lunar-ros) $$PS1" && exec bash --noprofile --norc -i'

deploy-dry-run:
	rsync -azvn --itemize-changes -e "ssh $(RSYNC_SSH_OPTS)" $(RSYNC_EXCLUDES) $(DEPLOY_PATHS) $(JETSON_HOST):$(JETSON_DIR)/

deploy:
	rsync -azv --itemize-changes -e "ssh $(RSYNC_SSH_OPTS)" $(RSYNC_EXCLUDES) $(DEPLOY_PATHS) $(JETSON_HOST):$(JETSON_DIR)/
