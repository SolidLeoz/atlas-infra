#!/data/data/com.termux/files/usr/bin/bash

termux-wake-lock
termux-notification --title "Aurora" --content "Sistema in avvio..." --id aurora-boot
sleep 10

ENV_FILE="${AURORA_ENV_FILE:-$HOME/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

cd ~/aurora-mobile
python mobile_sensors.py
