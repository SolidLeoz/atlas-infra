# Aurora Infra Quickstart

Fast path to get the stack running and verified.

## 1) Prepare the env (all hosts)
1. Copy `.env.example` to `~/.env`.
2. Fill in Tailscale IPs, tokens, and passwords.
3. Link into each component folder: `ln -s ~/.env ./.env`

## 2) solidserver (core services)
### Mosquitto (TLS)
```bash
cd /home/leoz/aurora-infra-/solidserver/mosquitto
ENV_FILE=~/.env ./render-mosquitto-config.sh
sudo cp aurora.conf /etc/mosquitto/conf.d/aurora.conf
sudo systemctl restart mosquitto
```

### Edge hub (InfluxDB + Grafana + Telegraf collector)
```bash
cd /home/leoz/edge-hub
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

### solidserver agent (local metrics)
```bash
cd /home/leoz/aurora-infra-/solidserver/agent-solidserver
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

## 3) workstation / ofsc (agents)
```bash
# Place certs in ./certs (ca.crt, <device>.crt, <device>.key)
cd /home/leoz/aurora-infra-/workstation/aurora-agent-workstation
sudo docker compose up -d

cd /home/leoz/aurora-infra-/ofsc/aurora-agent-ofsc
docker compose up -d
```

## 4) xiaomi (Termux client)
```bash
# On the phone
cd ~/aurora-mobile
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
docker exec edge-hub-influxdb-1 influx query --org "$EDGE_INFLUX_ORG" --token "$EDGE_INFLUX_ADMIN_TOKEN" \
'from(bucket:"telemetry") |> range(start:-10m) |> limit(n:5)'
```

### Grafana
- URL: `http://solidserver:3001/`
- Dashboards: "Aurora Overview", "Aurora Device Detail"

## Common fixes
- No data in Grafana: check `edge-hub-telegraf-1` logs and MQTT traffic.
- TLS errors: verify cert names and permissions (`chmod 644 *.crt *.key`).
- Xiaomi CPU/uptime missing: Android restricts `/proc`; client uses `top`/`uptime` fallback.
