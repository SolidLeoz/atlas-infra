#!/data/data/com.termux/files/usr/bin/bash

termux-wake-lock
sleep 10

ENV_FILE="${AURORA_ENV_FILE:-$HOME/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

cd ~/aurora-mobile
nohup python mobile_sensors.py > nohup.out 2>&1 &

LOG_DIR="$HOME/.local/var/log"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/aurora-mobile.log"

BROKER_HOST="${XIAOMI_MQTT_BROKER_HOST:-}"
BROKER_PORT="${XIAOMI_MQTT_BROKER_PORT:-}"

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
    echo "[$(date -u +%FT%TZ)] starting aurora mobile node" >> "$LOG_FILE"
    python mobile_sensors.py >> "$LOG_FILE" 2>&1 || true
    echo "[$(date -u +%FT%TZ)] aurora mobile node exited; restarting in 3s" >> "$LOG_FILE"
    sleep 3
  done
) &
