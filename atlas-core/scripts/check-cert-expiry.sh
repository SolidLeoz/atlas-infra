#!/usr/bin/env bash
set -euo pipefail

# Controlla la scadenza di tutti i certificati .crt in una directory.
# Esce con codice 1 se almeno un certificato scade entro WARN_DAYS giorni.
#
# Uso:
#   ./check-cert-expiry.sh [CERT_DIR] [WARN_DAYS]
#   ./check-cert-expiry.sh /etc/mosquitto/certs 30
#
# Cron suggerito (check settimanale ogni lunedì alle 09:00):
#   0 9 * * 1 /path/to/atlas-infra/atlas-core/scripts/check-cert-expiry.sh /etc/mosquitto/certs 30

CERT_DIR="${1:-/etc/mosquitto/certs}"
WARN_DAYS="${2:-30}"
EXIT_CODE=0
CHECKED=0

if [[ ! -d "${CERT_DIR}" ]]; then
  echo "[ERR] Directory non trovata: ${CERT_DIR}" >&2
  exit 2
fi

for cert in "${CERT_DIR}"/*.crt; do
  [[ -f "$cert" ]] || continue
  CHECKED=$((CHECKED + 1))

  subject=$(openssl x509 -subject -noout -in "$cert" 2>/dev/null | sed 's/subject=//')
  expiry=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2)
  expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$expiry" +%s 2>/dev/null)
  now_epoch=$(date +%s)
  days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

  if [[ "$days_left" -lt 0 ]]; then
    echo "[CRITICAL] $cert (${subject}) — SCADUTO da $(( -days_left )) giorni!"
    EXIT_CODE=1
  elif [[ "$days_left" -lt "$WARN_DAYS" ]]; then
    echo "[WARN] $cert (${subject}) — scade tra ${days_left} giorni ($expiry)"
    EXIT_CODE=1
  else
    echo "[OK] $cert (${subject}) — ${days_left} giorni rimanenti"
  fi
done

if [[ "$CHECKED" -eq 0 ]]; then
  echo "[WARN] Nessun certificato .crt trovato in ${CERT_DIR}"
  exit 2
fi

echo ""
echo "Certificati controllati: ${CHECKED}, soglia avviso: ${WARN_DAYS} giorni"
exit $EXIT_CODE
