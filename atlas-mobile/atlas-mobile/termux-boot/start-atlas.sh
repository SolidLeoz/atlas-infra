#!/data/data/com.termux/files/usr/bin/bash

termux-wake-lock
sleep 10

ENV_FILE="${ATLAS_ENV_FILE:-$HOME/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

cd ~/atlas-mobile
nohup python mobile_sensors.py > nohup.out 2>&1 &

LOG_DIR="$HOME/.local/var/log"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/atlas-mobile.log"

BROKER_HOST="${ATLAS_MOBILE_MQTT_BROKER_HOST:-}"
BROKER_PORT="${ATLAS_MOBILE_MQTT_BROKER_PORT:-}"

if [ -n "$BROKER_HOST" ] && [ -n "$BROKER_PORT" ]; then
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if nc -zw 2 "$BROKER_HOST" "$BROKER_PORT" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

(
  while true; do
    echo "[$(date -u +%FT%TZ)] starting atlas mobile node (sensors)" >> "$LOG_FILE"
    python mobile_sensors.py >> "$LOG_FILE" 2>&1 || true
    echo "[$(date -u +%FT%TZ)] atlas mobile node (sensors) exited; restarting in 3s" >> "$LOG_FILE"
    sleep 3
  done
) &

(
  while true; do
    echo "[$(date -u +%FT%TZ)] starting atlas mobile watcher" >> "$LOG_FILE"
    python watcher.py >> "$LOG_FILE" 2>&1 || true
    echo "[$(date -u +%FT%TZ)] atlas mobile watcher exited; restarting in 3s" >> "$LOG_FILE"
    sleep 3
  done
) &
