# Atlas Research Infrastructure

Atlas Research Infrastructure (Atlas Infra) is a TLS-first telemetry stack for a Tailscale network. It uses
MQTT + Telegraf to collect metrics, InfluxDB to store them, and Grafana to
visualize them. atlas-core hosts the core services; other devices publish
telemetry via MQTT with X.509 client certificates.

## Architecture
- atlas-core: Mosquitto (TLS), InfluxDB, Grafana, Telegraf collector,
  Telegraf agent, optional IoT gateway.
- atlas-lab + atlas-field: Telegraf agents publishing to MQTT over TLS.
- atlas-mobile: Termux client publishing battery and system telemetry.

Data flow:
devices -> MQTT TLS -> telegraf collector -> InfluxDB -> Grafana

## Repository layout
- `atlas-core/edge-hub`: InfluxDB, Grafana, telegraf collector (MQTT input).
- `atlas-core/mosquitto`: Mosquitto TLS config template + render script.
- `atlas-core/atlas-agent-core`: Telegraf agent for atlas-core.
- `atlas-core/iot-gateway`: Optional gateway publishing sensors to MQTT.
- `atlas-lab/atlas-agent-lab`: Telegraf agent for atlas-lab.
- `atlas-field/atlas-agent-field`: Telegraf agent for atlas-field.
- `atlas-mobile/atlas-mobile`: Termux telemetry client.
- `GUIDELINE.MD`: Detailed notes (Italian).
- `.env.example`: Central environment template (copy to `~/.env`).

## Requirements
- Docker + Docker Compose on atlas-core, atlas-lab, atlas-field.
- Tailscale installed and connected on all hosts.
- X.509 certificates for broker and clients (see `GUIDELINE.MD`).

## Configuration
1. Copy `.env.example` to `~/.env` on each device.
2. Fill in Tailscale IPs, tokens, and passwords.
3. Link the env file into each component directory:
   `ln -s ~/.env ./.env`

## Setup (summary)
### atlas-core
1. Render Mosquitto config:
   `ENV_FILE=~/.env atlas-core/mosquitto/render-mosquitto-config.sh`
   then copy to `/etc/mosquitto/conf.d/atlas.conf` and restart mosquitto.
2. Start edge-hub:
   `cd atlas-core/edge-hub && docker compose up -d`
3. Start agent:
   `ENV_FILE=~/.env atlas-core/atlas-agent-core/render-runtime-config.sh`
   then `docker compose up -d`
4. (Optional) Start the IoT gateway in `atlas-core/iot-gateway`.

### atlas-lab / atlas-field
1. Place certs in `./certs` (`ca.crt`, `<device>.crt`, `<device>.key`).
2. Link `~/.env` into the agent folder.
3. `docker compose up -d`

### atlas-mobile
1. Copy `atlas-mobile/atlas-mobile` to `~/atlas-mobile` in Termux.
2. Link `~/.env` into that folder.
3. Install Python deps: `pip install paho-mqtt pyyaml`.
4. Start: `python mobile_sensors.py`

Optional env:
- `ATLAS_MOBILE_DISK_PATH` (default `~/`) for disk usage path.

## Grafana
- URL: `http://atlas-core:3001` (Tailscale)
- Dashboards: "Atlas Overview", "Atlas Device Detail"
- Credentials from `EDGE_GRAFANA_ADMIN_USER` / `EDGE_GRAFANA_ADMIN_PASSWORD`

## Troubleshooting
- No data in Grafana:
  - Check MQTT with `mosquitto_sub` on atlas-core.
  - Check `edge-hub-telegraf-1` logs.
  - Verify device certs and CN match device IDs.
- Atlas mobile only shows battery:
  - Ensure `mobile_sensors.py` is updated; it now publishes cpu/mem/disk/system.

## Notes
- External MQTT traffic is TLS-only on port 8883.
- Keep `.env` and certs out of Git (see `.gitignore`).
- The legacy `atlas-field/atlas-dashboard` is deprecated; use atlas-core Grafana.
