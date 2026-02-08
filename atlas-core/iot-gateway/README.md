# 🌐 IoT Gateway Edge-to-Cloud

Sistema completo di gateway IoT per comunicazione sicura edge-to-cloud con telemetria real-time e gestione comandi remoti.

## 🏗️ Architettura
```
Gateway IoT (Edge) ←→ [MQTTS/TLS] ←→ Broker MQTT (Cloud)
```

### Componenti:
- **Gateway containerizzato** (Docker)
- **Comunicazione MQTT/MQTTS** con mutual TLS (X.509)
- **Telemetria periodica** (temperatura simulata, CPU reale)
- **Comandi remoti** per configurazione runtime
- **Logging strutturato** e gestione errori

## 🔐 Sicurezza

- ✅ TLS/SSL obbligatorio (porta 8883)
- ✅ Autenticazione mutua con certificati X.509
- ✅ Subject Alternative Names (SAN)
- ✅ User non-root nei container
- ✅ Config e certificati read-only

## 🚀 Quick Start

### Prerequisiti
- Docker & Docker Compose
- Broker MQTT (Mosquitto) configurato con TLS
- Certificati X.509 (CA, server, client)

### Setup

1. **Configura certificati**:
```bash
mkdir -p certs
# Copia ca.crt, client.crt, client.key in certs/
```

2. **Configura gateway**:
```bash
cp config/gateway.yaml.example config/gateway.yaml
# Modifica broker IP, porta, topics
```

3. **Avvia gateway**:
```bash
docker-compose up -d
```

4. **Verifica logs**:
```bash
docker-compose logs -f
```

## 📊 Funzionalità

### Telemetria
```json
{
  "timestamp": "2026-02-01T12:00:00Z",
  "device_id": "gateway-atlas-core",
  "sensors": {
    "temperature": 23.4,
    "cpu_usage": 5.2
  }
}
```
**Topic**: `devices/{device-id}/telemetry`

### Comandi Remoti
```json
{
  "action": "set_interval",
  "value": 10
}
```
**Topic**: `devices/{device-id}/commands`

## 🛠️ Stack Tecnologico

- **Container**: Docker, Docker Compose
- **Linguaggio**: Python 3.11
- **MQTT**: Paho-MQTT
- **Config**: YAML
- **Logging**: Python logging (file + console)
- **Security**: OpenSSL, TLS 1.3

## 📁 Struttura Progetto
```
iot-gateway/
├── app.py                  # Applicazione principale
├── Dockerfile              # Build immagine Docker
├── docker-compose.yml      # Orchestrazione container
├── requirements.txt        # Dipendenze Python
├── config/
│   └── gateway.yaml.example  # Template configurazione
├── certs/                  # Certificati TLS (git-ignored)
└── logs/                   # Log applicativi (git-ignored)
```

## 🔧 Configurazione

File `config/gateway.yaml`:
```yaml
mqtt:
  broker: "broker.example.com"
  port: 8883
  client_id: "gateway-001"
  tls:
    enabled: true
    ca_cert: "/app/certs/ca.crt"
    client_cert: "/app/certs/client.crt"
    client_key: "/app/certs/client.key"
  topics:
    telemetry: "devices/gateway-001/telemetry"
    commands: "devices/gateway-001/commands"

sensors:
  temperature:
    interval: 5
    min: 18.0
    max: 28.0

logging:
  level: "INFO"
  file: "/app/logs/gateway.log"
```

## 🧪 Testing

### Sottoscrivi telemetria:
```bash
mosquitto_sub -h broker.example.com -p 8883 \
  --cafile certs/ca.crt \
  --cert certs/client.crt \
  --key certs/client.key \
  -t "devices/+/telemetry" -v
```

### Invia comando:
```bash
mosquitto_pub -h broker.example.com -p 8883 \
  --cafile certs/ca.crt \
  --cert certs/client.crt \
  --key certs/client.key \
  -t "devices/gateway-001/commands" \
  -m '{"action":"set_interval","value":10}'
```

## 📈 Monitoring
```bash
# Log real-time
docker-compose logs -f

# Stato container
docker-compose ps

# Statistiche risorse
docker stats iot-gateway
```

## 🔍 Troubleshooting

### Gateway non si connette:
```bash
# Verifica connettività broker
ping broker.example.com
nc -zv broker.example.com 8883

# Testa handshake TLS
openssl s_client -connect broker.example.com:8883 \
  -CAfile certs/ca.crt -cert certs/client.crt -key certs/client.key
```

### Errori certificati:
```bash
# Verifica validità certificati
openssl x509 -in certs/client.crt -text -noout
openssl verify -CAfile certs/ca.crt certs/client.crt
```

## 📄 Licenza

Progetto didattico - Leonardo Pericoli (2026)

## 📧 Contatti

- LinkedIn: [leonardo-pericoli-fullstack](https://linkedin.com/in/leonardo-pericoli-fullstack/)
- Email: pericolileonardo@gmail.com
