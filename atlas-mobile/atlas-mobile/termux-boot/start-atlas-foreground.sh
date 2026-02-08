#!/data/data/com.termux/files/usr/bin/bash

termux-wake-lock
termux-notification --title "Atlas" --content "Sistema in avvio..." --id atlas-boot
sleep 10

ENV_FILE="${ATLAS_ENV_FILE:-$HOME/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

cd ~/atlas-mobile
python mobile_sensors.py
