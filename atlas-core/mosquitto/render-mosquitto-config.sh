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

: "${MOSQUITTO_PLAIN_PORT:?missing MOSQUITTO_PLAIN_PORT}"
: "${MOSQUITTO_PLAIN_BIND_ADDR:?missing MOSQUITTO_PLAIN_BIND_ADDR}"
: "${MOSQUITTO_TLS_PORT:?missing MOSQUITTO_TLS_PORT}"
: "${MOSQUITTO_TLS_BIND_ADDR:?missing MOSQUITTO_TLS_BIND_ADDR}"
: "${MOSQUITTO_CAFILE:?missing MOSQUITTO_CAFILE}"
: "${MOSQUITTO_CERTFILE:?missing MOSQUITTO_CERTFILE}"
: "${MOSQUITTO_KEYFILE:?missing MOSQUITTO_KEYFILE}"

MOSQUITTO_ACL_LINE=""
if [[ -n "${MOSQUITTO_ACL_FILE:-}" ]]; then
  if [[ ! -f "${MOSQUITTO_ACL_FILE}" ]]; then
    echo "[ERR] MOSQUITTO_ACL_FILE non trovato: ${MOSQUITTO_ACL_FILE}" >&2
    exit 1
  fi
  MOSQUITTO_ACL_LINE="acl_file ${MOSQUITTO_ACL_FILE}"
fi
export MOSQUITTO_ACL_LINE

if ! command -v envsubst >/dev/null 2>&1; then
  echo "[ERR] envsubst non trovato. Installa con: sudo apt-get update && sudo apt-get install -y gettext-base" >&2
  exit 1
fi

envsubst < atlas.conf.template > atlas.conf
chmod 640 atlas.conf

echo "[OK] Config generata: $(pwd)/atlas.conf"
echo "     Installa con: sudo cp atlas.conf /etc/mosquitto/conf.d/atlas.conf"
