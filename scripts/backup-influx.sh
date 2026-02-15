#!/usr/bin/env bash
set -euo pipefail

# Atlas Research Infrastructure - InfluxDB Backup Script
# Performs a hot backup of the InfluxDB 2.x data.

# Load environment variables if available
if [[ -f "../.env" ]]; then
    source "../.env"
fi

BACKUP_DIR=${1:-"./backups"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL_BACKUP_PATH="$BACKUP_DIR/influxdb_backup_$TIMESTAMP"

# Check if influxdb container is running
if ! docker ps | grep -q edge-hub-influxdb-1; then
    echo "[ERR] InfluxDB container (edge-hub-influxdb-1) is not running."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "===> Starting InfluxDB backup to $FINAL_BACKUP_PATH"

# Run backup inside the container
docker exec edge-hub-influxdb-1 
    influx backup /tmp/backup 
    --token "${EDGE_INFLUX_ADMIN_TOKEN}"

# Copy backup from container to host
docker cp edge-hub-influxdb-1:/tmp/backup "$FINAL_BACKUP_PATH"

# Cleanup container temp files
docker exec edge-hub-influxdb-1 rm -rf /tmp/backup

echo "===> Backup completed: $FINAL_BACKUP_PATH"
echo "===> Compressing backup..."
tar -czf "${FINAL_BACKUP_PATH}.tar.gz" -C "$BACKUP_DIR" "influxdb_backup_$TIMESTAMP"
rm -rf "$FINAL_BACKUP_PATH"

echo "===> Final archive: ${FINAL_BACKUP_PATH}.tar.gz"
