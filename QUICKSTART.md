# Atlas Research Infrastructure Quickstart

Fast path to get the stack running and verified.

## 1) Prepare the env (all hosts)
1. Copy `.env.example` to `~/.env`.
2. Fill in Tailscale IPs, tokens, and passwords.
   - Create least-privilege Influx tokens:
     - `EDGE_INFLUX_TELEGRAF_TOKEN` (write to `telemetry`)
     - `EDGE_INFLUX_GRAFANA_TOKEN` (read from `telemetry`)
   - Keep `EDGE_INFLUX_ADMIN_TOKEN` for setup only.
3. Link into each component folder: `ln -s ~/.env ./.env`

## 2) atlas-core (core services)
### Mosquitto (TLS)
```bash
cd /home/leoz/atlas-infra/atlas-core/mosquitto
ENV_FILE=~/.env ./render-mosquitto-config.sh
sudo cp atlas.conf /etc/mosquitto/conf.d/atlas.conf
sudo systemctl restart mosquitto
```

### Edge hub (InfluxDB + Grafana + Telegraf collector)
```bash
cd /home/leoz/atlas-infra/atlas-core/edge-hub
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

### atlas-core agent (local metrics)
```bash
cd /home/leoz/atlas-infra/atlas-core/atlas-agent-core
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

## 3) atlas-lab / atlas-field (agents)
```bash
# Place certs in ./certs (ca.crt, <device>.crt, <device>.key)
cd /home/leoz/atlas-infra/atlas-lab/atlas-agent-lab
sudo docker compose up -d

cd /home/leoz/atlas-infra/atlas-field/atlas-agent-field
docker compose up -d
```

## 4) atlas-mobile (Termux client)
```bash
# On the phone
cd ~/atlas-mobile
python mobile_sensors.py
```

## 5) Verify
### MQTT
```bash
mosquitto_sub -h 127.0.0.1 -p 1883 -t 'devices/+/telemetry' -C 1 -W 10
```

### InfluxDB (last 10m)
```bash
source ~/.env
docker exec edge-hub-influxdb-1 influx query --org "$EDGE_INFLUX_ORG" --token "$EDGE_INFLUX_GRAFANA_TOKEN" \
'from(bucket:"telemetry") |> range(start:-10m) |> limit(n:5)'
```
If you only have the admin token, replace `EDGE_INFLUX_GRAFANA_TOKEN` with
`EDGE_INFLUX_ADMIN_TOKEN`.

### Grafana
- URL: `http://atlas-core:3001/`
- Dashboards: "Atlas Overview", "Atlas Device Detail"

## Common fixes
- No data in Grafana: check `edge-hub-telegraf-1` logs and MQTT traffic.
- TLS errors: verify cert names and permissions (`chmod 644 *.crt *.key`).
- Atlas mobile CPU/uptime missing: Android restricts `/proc`; client uses `top`/`uptime` fallback.
