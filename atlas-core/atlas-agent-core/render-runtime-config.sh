#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -z "${ENV_FILE:-}" ]]; then
  for candidate in ".env" "../.env" "../../.env"; do
    if [[ -f "${candidate}" ]]; then
      ENV_FILE="${candidate}"
      break
    fi
  done
fi

if [[ -z "${ENV_FILE:-}" || ! -f "${ENV_FILE}" ]]; then
  echo "[ERR] Env file mancante: ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a

mkdir -p _local_runtime

if ! command -v envsubst >/dev/null 2>&1; then
  echo "[ERR] envsubst non trovato. Installa con: sudo apt-get update && sudo apt-get install -y gettext-base" >&2
  exit 1
fi

: "${ATLAS_CORE_AGENT_MQTT_URL:?missing ATLAS_CORE_AGENT_MQTT_URL}"
: "${ATLAS_CORE_AGENT_DEVICE_ID:?missing ATLAS_CORE_AGENT_DEVICE_ID}"
: "${ATLAS_CORE_AGENT_TELEGRAF_HOSTNAME:?missing ATLAS_CORE_AGENT_TELEGRAF_HOSTNAME}"

envsubst < telegraf.conf.template > _local_runtime/telegraf.conf
cp -f _local_runtime/telegraf.conf telegraf.conf
chmod 644 telegraf.conf

echo "[OK] Runtime config generata: telegraf.conf"
