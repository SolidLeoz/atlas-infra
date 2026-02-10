#!/usr/bin/env bash
set -euo pipefail

# Backup completo di InfluxDB con timestamp.
# Mantiene gli ultimi 7 backup e rimuove i più vecchi.
#
# Uso:
#   cd atlas-core/edge-hub && ./scripts/influxdb-backup.sh
#
# Cron suggerito (backup giornaliero alle 03:00):
#   0 3 * * * cd /path/to/atlas-infra/atlas-core/edge-hub && ./scripts/influxdb-backup.sh >> /var/log/atlas-backup.log 2>&1

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

: "${EDGE_INFLUX_ORG:?missing EDGE_INFLUX_ORG}"
: "${EDGE_INFLUX_ADMIN_TOKEN:?missing EDGE_INFLUX_ADMIN_TOKEN}"

BACKUP_DIR="${INFLUX_BACKUP_DIR:-/opt/atlas-backups/influxdb}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${TARGET}"

echo "[INFO] Avvio backup InfluxDB → ${TARGET}"

docker exec edge-hub-influxdb-1 influx backup /tmp/backup \
  --org "${EDGE_INFLUX_ORG}" \
  --token "${EDGE_INFLUX_ADMIN_TOKEN}"

docker cp edge-hub-influxdb-1:/tmp/backup/. "${TARGET}/"
docker exec edge-hub-influxdb-1 rm -rf /tmp/backup

# Pulizia backup vecchi (mantieni ultimi 7)
# shellcheck disable=SC2012
ls -dt "${BACKUP_DIR}"/*/ 2>/dev/null | tail -n +8 | xargs rm -rf 2>/dev/null || true

BACKUP_SIZE=$(du -sh "${TARGET}" | cut -f1)
echo "[OK] Backup InfluxDB completato: ${TARGET} (${BACKUP_SIZE})"
