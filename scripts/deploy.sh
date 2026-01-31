#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-indy-the-agent}
CONTAINER_NAME=${CONTAINER_NAME:-indy-the-agent}
PORT=${PORT:-8000}
ENV_FILE=${ENV_FILE:-.env}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but not installed or not on PATH." >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

cd "$ROOT_DIR"

echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" .

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

RUN_ARGS=(
  --name "$CONTAINER_NAME"
  -p "${PORT}:8000"
  -e PYTHONUNBUFFERED=1
)

if [[ -f "$ENV_FILE" ]]; then
  RUN_ARGS+=(--env-file "$ENV_FILE")
fi

echo "Starting container: $CONTAINER_NAME on port $PORT"
docker run -d "${RUN_ARGS[@]}" "$IMAGE_NAME" >/dev/null

echo "Container is running. Logs: docker logs -f $CONTAINER_NAME"
