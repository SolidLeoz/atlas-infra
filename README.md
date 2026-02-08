# Aurora Infra

Aurora Infra is a TLS-first telemetry stack for a Tailscale network. It uses
MQTT + Telegraf to collect metrics, InfluxDB to store them, and Grafana to
visualize them. Solidserver hosts the core services; other devices publish
telemetry via MQTT with X.509 client certificates.

## Architecture
- solidserver: Mosquitto (TLS), InfluxDB, Grafana, Telegraf collector,
  Telegraf agent, optional IoT gateway.
- workstation + ofsc: Telegraf agents publishing to MQTT over TLS.
- xiaomi: Termux client publishing battery and system telemetry.

Data flow:
devices -> MQTT TLS -> telegraf collector -> InfluxDB -> Grafana

## Repository layout
- `solidserver/edge-hub`: InfluxDB, Grafana, telegraf collector (MQTT input).
- `solidserver/mosquitto`: Mosquitto TLS config template + render script.
- `solidserver/agent-solidserver`: Telegraf agent for solidserver.
- `solidserver/iot-gateway`: Optional gateway publishing sensors to MQTT.
- `workstation/aurora-agent-workstation`: Telegraf agent for workstation.
- `ofsc/aurora-agent-ofsc`: Telegraf agent for OFSC.
- `xiaomi/aurora-mobile`: Termux telemetry client.
- `GUIDELINE.MD`: Detailed notes (Italian).
- `.env.example`: Central environment template (copy to `~/.env`).

## Requirements
- Docker + Docker Compose on solidserver, workstation, ofsc.
- Tailscale installed and connected on all hosts.
- X.509 certificates for broker and clients (see `GUIDELINE.MD`).

## Configuration
1. Copy `.env.example` to `~/.env` on each device.
2. Fill in Tailscale IPs, tokens, and passwords.
3. Link the env file into each component directory:
   `ln -s ~/.env ./.env`

## Setup (summary)
### solidserver
1. Render Mosquitto config:
   `ENV_FILE=~/.env solidserver/mosquitto/render-mosquitto-config.sh`
   then copy to `/etc/mosquitto/conf.d/aurora.conf` and restart mosquitto.
2. Start edge-hub:
   `cd solidserver/edge-hub && docker compose up -d`
3. Start agent:
   `ENV_FILE=~/.env solidserver/agent-solidserver/render-runtime-config.sh`
   then `docker compose up -d`
4. (Optional) Start the IoT gateway in `solidserver/iot-gateway`.

### workstation / ofsc
1. Place certs in `./certs` (`ca.crt`, `<device>.crt`, `<device>.key`).
2. Link `~/.env` into the agent folder.
3. `docker compose up -d`

### xiaomi
1. Copy `xiaomi/aurora-mobile` to `~/aurora-mobile` in Termux.
2. Link `~/.env` into that folder.
3. Install Python deps: `pip install paho-mqtt pyyaml`.
4. Start: `python mobile_sensors.py`

Optional env:
- `XIAOMI_DISK_PATH` (default `~/`) for disk usage path.

## Grafana
- URL: `http://solidserver:3001` (Tailscale)
- Dashboards: "Aurora Overview", "Aurora Device Detail"
- Credentials from `EDGE_GRAFANA_ADMIN_USER` / `EDGE_GRAFANA_ADMIN_PASSWORD`

## Troubleshooting
- No data in Grafana:
  - Check MQTT with `mosquitto_sub` on solidserver.
  - Check `edge-hub-telegraf-1` logs.
  - Verify device certs and CN match device IDs.
- Xiaomi only shows battery:
  - Ensure `mobile_sensors.py` is updated; it now publishes cpu/mem/disk/system.

## Notes
- External MQTT traffic is TLS-only on port 8883.
- Keep `.env` and certs out of Git (see `.gitignore`).
- The legacy `ofsc/aurora-dashboard` is deprecated; use solidserver Grafana.
