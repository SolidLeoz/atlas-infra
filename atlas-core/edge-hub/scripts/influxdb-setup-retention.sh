#!/usr/bin/env bash
set -euo pipefail

# Imposta retention sul bucket telemetry.
# Eseguire una volta dopo il primo deploy, o quando si vuole cambiare la retention.
#
# Uso:
#   cd atlas-core/edge-hub && ./scripts/influxdb-setup-retention.sh
#
# Richiede: .env con EDGE_INFLUX_BUCKET, EDGE_INFLUX_ORG, EDGE_INFLUX_ADMIN_TOKEN

cd "$(dirname "$0")/.."

if [[ -z "${ENV_FILE:-}" ]]; then
  for candidate in ".env" "../.env" "../../.env"; do
    if [[ -f "${candidate}" ]]; then
      ENV_FILE="${candidate}"
      break
    fi
  done
fi

if [[ -z "${ENV_FILE:-}" || ! -f "${ENV_FILE}" ]]; then
  echo "[ERR] Env file mancante" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a

: "${EDGE_INFLUX_BUCKET:?missing EDGE_INFLUX_BUCKET}"
: "${EDGE_INFLUX_ORG:?missing EDGE_INFLUX_ORG}"
: "${EDGE_INFLUX_ADMIN_TOKEN:?missing EDGE_INFLUX_ADMIN_TOKEN}"

RETENTION_HOURS="${EDGE_INFLUX_RETENTION_HOURS:-2160}"

docker exec edge-hub-influxdb-1 influx bucket update \
  --name "${EDGE_INFLUX_BUCKET}" \
  --retention "${RETENTION_HOURS}h" \
  --org "${EDGE_INFLUX_ORG}" \
  --token "${EDGE_INFLUX_ADMIN_TOKEN}"

echo "[OK] Retention impostata a ${RETENTION_HOURS}h per bucket '${EDGE_INFLUX_BUCKET}'"
