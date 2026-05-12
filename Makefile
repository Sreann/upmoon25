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

.PHONY: build up down restart shell sim dashboard run kill logs check monitor keyboard config shell-env ros-shell install deploy deploy-dry-run help

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
	@echo "  make dashboard - Launch the dashboard in the container"
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
