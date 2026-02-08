#!/usr/bin/env bash
set -euo pipefail

# Renderizza i file di runtime a partire dai template e dalle env locali.
# NON committare i file generati (contengono token/password).

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

# Carica .env in modo sicuro (senza echo).
set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a

# Verifica variabili richieste (no hardcoded di indirizzi o token)
: "${EDGE_TELEGRAF_HOSTNAME:?missing EDGE_TELEGRAF_HOSTNAME}"
: "${EDGE_MQTT_URL:?missing EDGE_MQTT_URL}"
: "${EDGE_INFLUX_URL_TELEGRAF:?missing EDGE_INFLUX_URL_TELEGRAF}"
: "${EDGE_INFLUX_URL_GRAFANA:?missing EDGE_INFLUX_URL_GRAFANA}"
: "${EDGE_INFLUX_ORG:?missing EDGE_INFLUX_ORG}"
: "${EDGE_INFLUX_BUCKET:?missing EDGE_INFLUX_BUCKET}"

use_admin_fallback=false
if [[ -z "${EDGE_INFLUX_TELEGRAF_TOKEN:-}" || -z "${EDGE_INFLUX_GRAFANA_TOKEN:-}" ]]; then
  use_admin_fallback=true
fi

if [[ -z "${EDGE_INFLUX_TELEGRAF_TOKEN:-}" && -z "${EDGE_INFLUX_GRAFANA_TOKEN:-}" ]]; then
  : "${EDGE_INFLUX_ADMIN_TOKEN:?missing EDGE_INFLUX_ADMIN_TOKEN (or set EDGE_INFLUX_TELEGRAF_TOKEN and EDGE_INFLUX_GRAFANA_TOKEN)}"
fi

EDGE_INFLUX_TELEGRAF_TOKEN="${EDGE_INFLUX_TELEGRAF_TOKEN:-${EDGE_INFLUX_ADMIN_TOKEN:-}}"
EDGE_INFLUX_GRAFANA_TOKEN="${EDGE_INFLUX_GRAFANA_TOKEN:-${EDGE_INFLUX_ADMIN_TOKEN:-}}"
EDGE_INFLUX_TLS_SKIP_VERIFY="${EDGE_INFLUX_TLS_SKIP_VERIFY:-true}"

: "${EDGE_INFLUX_TELEGRAF_TOKEN:?missing EDGE_INFLUX_TELEGRAF_TOKEN}"
: "${EDGE_INFLUX_GRAFANA_TOKEN:?missing EDGE_INFLUX_GRAFANA_TOKEN}"

export EDGE_INFLUX_TELEGRAF_TOKEN EDGE_INFLUX_GRAFANA_TOKEN EDGE_INFLUX_TLS_SKIP_VERIFY

if [[ "${use_admin_fallback}" == "true" ]]; then
  echo "[WARN] Using EDGE_INFLUX_ADMIN_TOKEN as fallback. Create least-privilege tokens." >&2
fi

mkdir -p _local_runtime provisioning/datasources

# Richiede envsubst (pacchetto gettext-base su Ubuntu)
if ! command -v envsubst >/dev/null 2>&1; then
  echo "[ERR] envsubst non trovato. Installa con: sudo apt-get update && sudo apt-get install -y gettext-base" >&2
  exit 1
fi

# Render Grafana datasource (contiene token)
envsubst < provisioning/datasources/influxdb.yml.template > _local_runtime/influxdb.yml

# Render Telegraf config (contiene token)
envsubst < telegraf.conf.template > _local_runtime/telegraf.conf

# Copia nei path attesi dai container (file reali)
cp -f _local_runtime/influxdb.yml provisioning/datasources/influxdb.yml
cp -f _local_runtime/telegraf.conf telegraf.conf

chmod 644 provisioning/datasources/influxdb.yml telegraf.conf

echo "[OK] Runtime config generata:"
echo " - provisioning/datasources/influxdb.yml"
echo " - telegraf.conf"
