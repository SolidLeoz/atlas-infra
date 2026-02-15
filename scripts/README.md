# Atlas Infra - Operational Scripts

This directory contains scripts for maintaining and managing the Atlas Research Infrastructure.

## 1. Certificate Automation (`generate-certs.sh`)
Automates the creation of the PKI (Public Key Infrastructure) for Mutual TLS.
- Generates a Root CA.
- Generates Broker certificates with Subject Alternative Names (SAN).
- Generates Client certificates for all defined devices.

**Usage:**
```bash
./generate-certs.sh ./my_certs
```
*Note: Set `ATLAS_BROKER_IP` environment variable to include the correct Tailscale IP in the broker certificate.*

## 2. InfluxDB Backup (`backup-influx.sh`)
Performs a hot backup of the InfluxDB 2.x database without stopping the service.
- Creates a snapshot of the data.
- Compresses the backup into a `.tar.gz` archive.
- Automatically cleans up temporary files in the container.

**Usage:**
```bash
./backup-influx.sh /path/to/backups
```

## 3. Health Checks (Built-in)
Docker containers are now configured with native health checks:
- **InfluxDB:** Uses `influx ping`.
- **Grafana:** Uses `wget` against the `/api/health` endpoint.
- **Telegraf Agents:** Monitors the process state.

Use `docker ps` to see the health status:
```bash
docker ps --format "table {{.Names}}	{{.Status}}"
```
