# Atlas Research Infrastructure

## Purpose
Atlas Research Infrastructure (Atlas Infra) is a TLS-first telemetry and
observability stack for a Tailscale network. It standardizes how multiple
devices publish system metrics to a central broker and how those metrics are
stored and visualized for academic or lab research workflows.

## System roles
- atlas-core (solidserver): central hub. Runs Mosquitto (systemd), InfluxDB,
  Grafana, and the MQTT -> Influx Telegraf collector. Optionally runs an
  IoT gateway for synthetic sensor data.
- atlas-lab (workstation): Telegraf agent publishing system metrics over MQTT
  TLS.
- atlas-field (ofsc): Telegraf agent publishing system metrics over MQTT TLS.
- atlas-mobile (xiaomi): Termux Python client publishing battery + system
  telemetry over MQTT TLS.

## Data flow
1. Agents and mobile publish to MQTT topics:
   - devices/<device>/telemetry
   - devices/<device>/sensors/*
2. On atlas-core, Telegraf subscribes to MQTT and writes to InfluxDB.
3. Grafana dashboards read from InfluxDB for visualization.

## Security model
- Mutual TLS (X.509) for all external MQTT connections.
- Least-privilege Influx tokens: separate read token (Grafana) and write token
  (Telegraf). Admin token is for bootstrap only.
- Centralized secrets and addresses in a single .env file per host.
- Runtime configs are generated via templates and envsubst; they are not
  committed to Git.
- Grafana is exposed only on the Tailscale interface by default.

## What this repository contains
- Source templates and scripts for Mosquitto, Telegraf, InfluxDB, and Grafana.
- Provisioned Grafana dashboards and datasource templates.
- Mobile telemetry client and termux boot scripts.
- Documentation for setup and operations.

What is not in the repo:
- Secrets, tokens, private keys, or runtime configs.
- Generated files in _local_runtime/ or local telegraf.conf outputs.

## Deploying to another lab

### Prerequisites
- Ubuntu 24.04+ on atlas-core / atlas-lab / atlas-field.
- Docker + Docker Compose installed on atlas-core / atlas-lab / atlas-field.
- Tailscale installed and connected on all hosts.
- Mosquitto installed and enabled on atlas-core (systemd).
- Termux + Python on atlas-mobile.

### 1) Clone the repo on each host
```bash
git clone git@github.com:SolidLeoz/atlas-infra.git
```

### 2) Create a central env file (per host)
```bash
cp atlas-infra/.env.example ~/.env
```
Edit values for:
- Tailscale IPs
- Influx/Grafana credentials
- MQTT broker address
- Influx tokens:
  - `EDGE_INFLUX_TELEGRAF_TOKEN` (write)
  - `EDGE_INFLUX_GRAFANA_TOKEN` (read)

Link the env into each component directory:
```bash
ln -s ~/.env ~/atlas-infra/atlas-core/edge-hub/.env
ln -s ~/.env ~/atlas-infra/atlas-core/atlas-agent-core/.env
ln -s ~/.env ~/atlas-infra/atlas-lab/atlas-agent-lab/.env
ln -s ~/.env ~/atlas-infra/atlas-field/atlas-agent-field/.env
```

### 3) Create TLS certificates (atlas-core)
Generate a CA and per-device certs. CN must match the device_id:
atlas-core, atlas-lab, atlas-field, atlas-mobile.
The broker certificate must include SAN for the atlas-core IP.

Example (run on atlas-core):
```bash
mkdir -p ~/mqtt-certs/atlas
cd ~/mqtt-certs/atlas
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 825 \
  -subj "/CN=Atlas Lab CA" -out ca.crt

openssl genrsa -out broker.key 2048
openssl req -new -key broker.key -subj "/CN=atlas-core" -out broker.csr
cat > broker.ext <<'EOF'
subjectAltName=IP:YOUR_ATLAS_CORE_TS_IP,DNS:atlas-core
EOF
openssl x509 -req -in broker.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out broker.crt -days 365 -sha256 -extfile broker.ext

for name in atlas-core atlas-lab atlas-field atlas-mobile; do
  openssl genrsa -out "${name}.key" 2048
  openssl req -new -key "${name}.key" -subj "/CN=${name}" -out "${name}.csr"
  openssl x509 -req -in "${name}.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out "${name}.crt" -days 365 -sha256
done
```

Distribute certs:
- atlas-core broker certs -> /etc/mosquitto/certs/
- agent certs -> <agent>/certs/
- atlas-mobile certs -> ~/atlas-mobile/certs/

### 4) Atlas-core setup
Render Mosquitto config and restart:
```bash
ENV_FILE=~/.env ~/atlas-infra/atlas-core/mosquitto/render-mosquitto-config.sh
sudo cp ~/atlas-infra/atlas-core/mosquitto/atlas.conf /etc/mosquitto/conf.d/atlas.conf
sudo systemctl restart mosquitto
```

Start edge-hub:
```bash
cd ~/atlas-infra/atlas-core/edge-hub
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

Start atlas-agent-core:
```bash
cd ~/atlas-infra/atlas-core/atlas-agent-core
ENV_FILE=~/.env ./render-runtime-config.sh
docker compose up -d
```

### 5) Atlas-lab and Atlas-field agents
Copy certs and start:
```bash
cd ~/atlas-infra/atlas-lab/atlas-agent-lab
docker compose up -d

cd ~/atlas-infra/atlas-field/atlas-agent-field
docker compose up -d
```

### 6) Atlas-mobile client
On the phone:
```bash
cp -r ~/atlas-infra/atlas-mobile/atlas-mobile ~/atlas-mobile
ln -s ~/.env ~/atlas-mobile/.env
pip install paho-mqtt pyyaml
python ~/atlas-mobile/mobile_sensors.py
```

### 7) Verify
On atlas-core:
```bash
mosquitto_sub -h 127.0.0.1 -p 1883 -t 'devices/+/telemetry' -C 1 -W 5

source ~/.env
docker exec edge-hub-influxdb-1 influx query --org "$EDGE_INFLUX_ORG" \
  --token "$EDGE_INFLUX_GRAFANA_TOKEN" \
  'from(bucket:"telemetry") |> range(start:-10m) |> limit(n:5)'
```

Grafana:
- URL: http://atlas-core:3001/ (MagicDNS) or http://<ATLAS_CORE_TS_IP>:3001/
- Credentials: EDGE_GRAFANA_ADMIN_USER / EDGE_GRAFANA_ADMIN_PASSWORD

## Notes
- If MagicDNS is not enabled, atlas-core will not resolve; use the Tailscale IP.
- For external access to Grafana, EDGE_GRAFANA_BIND_ADDR must be 0.0.0.0.
- If you use HTTPS for Influx, keep `EDGE_INFLUX_TLS_SKIP_VERIFY=false` and
  provide a valid CA.
- To enforce per-device MQTT ACLs, copy
  `atlas-core/mosquitto/acl.conf.example` to `/etc/mosquitto/acl.conf` and set
  `MOSQUITTO_ACL_FILE` in `.env`, then re-render the Mosquitto config.
