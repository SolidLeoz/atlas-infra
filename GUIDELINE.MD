# 🎙️ **DESIGN COMPLETO: AURORA VOICE ASSISTANT**

---

## 📐 **ARCHITETTURA DETTAGLIATA**

### **1. COMPONENTI SISTEMA**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORKSTATION (Central Brain)                          │
│                    ${AURORA_WORKSTATION_TS_IP} - Ubuntu + GPU 4060Ti                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              CONTAINER: aurora-voice-engine                      │ │
│  │  Port: 8000 (API), Network: aurora-net                          │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │  1. MQTT Subscriber (voice/+/audio/request)                     │ │
│  │     ↓ riceve audio Base64 da Xiaomi                             │ │
│  │                                                                  │ │
│  │  2. Whisper STT (faster-whisper + CUDA)                         │ │
│  │     ↓ audio → text transcription                                │ │
│  │     Model: whisper-large-v3 (GPU accelerated)                   │ │
│  │                                                                  │ │
│  │  3. Command Parser + LLM (Ollama llama3.2:3b)                   │ │
│  │     ↓ text → structured command                                 │ │
│  │     Extract: intent, target, parameters                         │ │
│  │                                                                  │ │
│  │  4. Action Executor                                             │ │
│  │     ├─ Query InfluxDB (metriche real-time)                      │ │
│  │     ├─ Publish MQTT commands (control devices)                  │ │
│  │     ├─ Query Docker (container status)                          │ │
│  │     └─ System commands (via subprocess)                         │ │
│  │                                                                  │ │
│  │  5. Response Generator (LLM + templates)                        │ │
│  │     ↓ risultato → risposta naturale italiana                    │ │
│  │                                                                  │ │
│  │  6. Piper TTS (it-IT voice)                                     │ │
│  │     ↓ text → audio WAV                                          │ │
│  │                                                                  │ │
│  │  7. MQTT Publisher (voice/+/audio/response)                     │ │
│  │     ↓ invia audio Base64 a Xiaomi                               │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              CONTAINER: aurora-ollama                            │ │
│  │  Port: 11434, GPU: enabled, Model: llama3.2:3b                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              EXISTING: Mosquitto MQTT Broker                     │ │
│  │  Port: 1883 (local), 8883 (TLS)                                 │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    SOLIDSERVER (Edge Hub)                               │
│                    ${AURORA_SOLIDSERVER_TS_IP} - Ubuntu 24.04                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  EXISTING: InfluxDB + Telegraf + Grafana                         │ │
│  │  - Fornisce dati per query vocali                               │ │
│  │  - Endpoint: ${EDGE_INFLUX_URL_TELEGRAF} (InfluxDB)             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  NUOVO: aurora-data-api                                          │ │
│  │  Port: 8001                                                      │ │
│  │  - REST API per query InfluxDB semplificate                     │ │
│  │  - Endpoints: /metrics/{device}/{type}                          │ │
│  │  - Cache 5s per ridurre latenza                                 │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    XIAOMI (Voice Interface)                             │
│                    ${AURORA_XIAOMI_TS_IP} - Android + Termux                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              aurora-mobile-client.py                             │ │
│  │  Python 3.11 in Termux                                           │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │  1. Wake Word Detection (PocketSphinx)                           │ │
│  │     Keyword: "Aurora" o "Hey Aurora"                            │ │
│  │     ↓ attiva registrazione                                       │ │
│  │                                                                  │ │
│  │  2. Audio Recorder (PyAudio)                                     │ │
│  │     ↓ registra 5s dopo wake word                                │ │
│  │     Format: WAV 16kHz mono                                       │ │
│  │                                                                  │ │
│  │  3. Audio Encoder                                                │ │
│  │     ↓ WAV → Base64                                              │ │
│  │                                                                  │ │
│  │  4. MQTT Publisher                                               │ │
│  │     Topic: voice/xiaomi/audio/request                           │ │
│  │     Payload: {audio: "base64...", user_id: "xiaomi"}           │ │
│  │     QoS: 1, TLS: enabled                                         │ │
│  │                                                                  │ │
│  │  5. MQTT Subscriber                                              │ │
│  │     Topic: voice/xiaomi/audio/response                          │ │
│  │     ↓ riceve risposta audio + text                              │ │
│  │                                                                  │ │
│  │  6. Audio Player (simpleaudio)                                   │ │
│  │     ↓ Base64 → WAV → play via speaker                           │ │
│  │                                                                  │ │
│  │  7. UI Termux (optional)                                         │ │
│  │     - Status LED (listening/processing/speaking)                │ │
│  │     - Text transcript display                                    │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 **FLUSSO COMPLETO CONVERSAZIONE**

```
1. UTENTE PARLA
   "Aurora, qual è la temperatura del server?"
   
   ↓ [Xiaomi mic]
   
2. WAKE WORD DETECTION
   Keyword "Aurora" detected → START recording
   
   ↓ [Record 5s audio]
   
3. ENCODE & PUBLISH
   audio.wav → base64 → MQTT
   Topic: voice/xiaomi/audio/request
   
   ↓ [MQTTS over Tailscale]
   
4. WORKSTATION RICEVE
   aurora-voice-engine subscribe
   
   ↓ [Decode Base64]
   
5. SPEECH-TO-TEXT (Whisper)
   audio → "Qual è la temperatura del server?"
   Tempo: ~1-2s (GPU accelerated)
   
   ↓ [Text extracted]
   
6. COMMAND PARSING (LLM)
   Prompt to Ollama:
   """
   Sei un assistente che estrae comandi strutturati.
   Input: "Qual è la temperatura del server?"
   Output JSON:
   {
     "intent": "query_metric",
     "target": "solidserver",
     "metric": "temperature",
     "action": "get_current_value"
   }
   """
   Tempo: ~500ms
   
   ↓ [Structured command]
   
7. ACTION EXECUTION
   a) Query InfluxDB via REST API:
      GET http://${AURORA_SOLIDSERVER_TS_IP}:8001/metrics/solidserver/temperature
      
   b) Response: {"value": 42.5, "unit": "celsius", "timestamp": "..."}
   
   Tempo: ~100ms
   
   ↓ [Data retrieved]
   
8. RESPONSE GENERATION (LLM)
   Prompt to Ollama:
   """
   Genera risposta naturale italiana:
   Query: temperatura server
   Result: 42.5°C
   Stile: assistente intelligente
   """
   
   Output: "La temperatura del server è di 42 gradi e mezzo."
   Tempo: ~300ms
   
   ↓ [Response text]
   
9. TEXT-TO-SPEECH (Piper)
   text → audio.wav (voce italiana femminile)
   Tempo: ~500ms
   
   ↓ [Audio generated]
   
10. ENCODE & PUBLISH
    audio.wav → base64 → MQTT
    Topic: voice/xiaomi/audio/response
    Payload: {
      "audio": "base64...",
      "text": "La temperatura del server...",
      "metadata": {...}
    }
    
    ↓ [MQTTS over Tailscale]
    
11. XIAOMI RICEVE
    aurora-mobile-client subscribe
    
    ↓ [Decode Base64]
    
12. PLAY AUDIO
    base64 → WAV → speaker output
    
    ↓ [Audio played]
    
13. UTENTE ASCOLTA
    "La temperatura del server è di 42 gradi e mezzo."

TEMPO TOTALE: ~3-4 secondi
```

---

## 📊 **TOPIC MQTT STRUCTURE**

```
aurora/
├── voice/
│   ├── xiaomi/
│   │   ├── audio/
│   │   │   ├── request          # Xiaomi → Workstation (audio queries)
│   │   │   └── response         # Workstation → Xiaomi (audio replies)
│   │   ├── status               # Xiaomi status (online/offline)
│   │   └── config               # Runtime config updates
│   │
│   └── commands/                # Direct commands (non-voice)
│       ├── restart/+
│       ├── status/+
│       └── action/+
│
├── devices/
│   ├── xiaomi/
│   │   ├── telemetry            # EXISTING: battery, sensors
│   │   └── sensors/#
│   │
│   ├── ofsc/telemetry           # EXISTING: system metrics
│   ├── workstation/telemetry    # EXISTING: system metrics
│   └── solidserver/telemetry    # system metrics + gateway sensors
│
└── system/
    ├── alerts/#                 # System-wide alerts
    ├── health/#                 # Health checks
    └── logs/#                   # Centralized logging
```

---

## 🗄️ **DATI NECESSARI PER INTEGRAZIONE**

### **A. MQTT Broker (Workstation)**
```yaml
Broker:
  Host: ${AURORA_WORKSTATION_TS_IP}
  Port TLS: 8883
  Port Local: 1883
  
Certificati esistenti:
  - CA: ~/mqtt-certs/ca.crt
  - Workstation: ~/mqtt-certs/workstation.{crt,key}
  
Nuovi certificati da generare:
  - aurora-engine: per voice-engine container
  - xiaomi-voice: per client vocale (separato da xiaomi telemetria)

Topics da sottoscrivere (voice-engine):
  - voice/+/audio/request
  - aurora/commands/#
  
Topics da pubblicare (voice-engine):
  - voice/+/audio/response
  - aurora/system/alerts/#
```

### **B. InfluxDB (Solidserver)**
```yaml
Database:
  Host: ${AURORA_SOLIDSERVER_TS_IP}:8086
  Org: ${EDGE_INFLUX_ORG}
  Bucket: telemetry
  Token: ${EDGE_INFLUX_ADMIN_TOKEN}
  
Measurements disponibili:
  - cpu (fields: usage_active, usage_idle, ...)
  - mem (fields: used_percent, available, ...)
  - disk (fields: used_percent, free, ...)
  - temp (fields: temp, sensor tag)
  - system (fields: load1, load5, load15, uptime)
  - sensors (device=solidserver: temperature, cpu_usage)

Query patterns comuni:
  1. Current value:
     from(bucket: "telemetry")
       |> range(start: -1m)
       |> filter(fn: (r) => r["device"] == "X")
       |> filter(fn: (r) => r["_measurement"] == "Y")
       |> filter(fn: (r) => r["_field"] == "Z")
       |> last()
  
  2. Average last 5min:
     |> range(start: -5m)
     |> mean()
  
  3. Max/Min last hour:
     |> range(start: -1h)
     |> max() / min()
```

### **C. Docker Networks (Workstation)**
```yaml
Network: bridge (default)
  - aurora-voice-engine
  - aurora-ollama
  - mosquitto (già esistente)

Volumes:
  - whisper-models: /models (cache modelli Whisper)
  - piper-voices: /voices (voci TTS italiane)
  - ollama-models: /root/.ollama (modelli LLM)
  
GPU Access:
  - device: /dev/nvidia0
  - runtime: nvidia
  - NVIDIA_VISIBLE_DEVICES: all
```

### **D. Xiaomi (Termux)**
```yaml
Packages Termux:
  - python (3.11)
  - portaudio (per PyAudio)
  - openssl (per MQTT TLS)
  - ffmpeg (codec audio)

Python packages:
  - paho-mqtt
  - pyaudio
  - pocketsphinx (wake word)
  - simpleaudio (playback)
  - base64 (stdlib)

Certificati:
  - ca.crt: ~/aurora-mobile/certs/
  - xiaomi-voice.crt
  - xiaomi-voice.key

Config file: ~/aurora-mobile/config.yaml
  mqtt:
    broker: ${AURORA_WORKSTATION_TS_IP}
    port: 8883
    client_id: ${XIAOMI_VOICE_CLIENT_ID}
    username: ${XIAOMI_VOICE_USERNAME}
  audio:
    wake_word: aurora
    sample_rate: 16000
    channels: 1
    record_duration: 5
```

---

## 🎯 **COMANDI VOCALI SUPPORTATI (MVP)**

### **1. QUERY METRICHE**
```
"Aurora, temperatura del server"
"Aurora, quanta CPU sta usando workstation"
"Aurora, memoria disponibile su ofsc"
"Aurora, carico sistema solidserver"
"Aurora, spazio disco workstation"
"Aurora, uptime di tutti i device"
```

### **2. CONTROLLO DISPOSITIVI**
```
"Aurora, riavvia gateway"
"Aurora, stato container su solidserver"
"Aurora, spegni Grafana"
"Aurora, avvia InfluxDB"
```

### **3. INFORMAZIONI SISTEMA**
```
"Aurora, quanti device sono online"
"Aurora, mostrami gli alert attivi"
"Aurora, quando è stato l'ultimo backup"
"Aurora, connessione MQTT funziona"
```

### **4. AUTOMAZIONI**
```
"Aurora, notificami se CPU supera 80%"
"Aurora, crea report giornaliero temperature"
"Aurora, alert se disco < 10GB"
```

---

## 📦 **FILE STRUCTURE PROGETTO**

```
~/aurora-infra-/
├── workstation/
│   └── aurora-agent-workstation/
│       ├── docker-compose.yml
│       ├── telegraf.conf
│       └── certs/
├── solidserver/
│   ├── edge-hub/
│   │   ├── docker-compose.yml
│   │   ├── telegraf.conf.template
│   │   ├── provisioning/
│   │   └── render-runtime-config.sh
│   ├── agent-solidserver/
│   │   ├── docker-compose.yml
│   │   ├── telegraf.conf.template
│   │   └── render-runtime-config.sh
│   ├── iot-gateway/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── config/
│   └── mosquitto/
│       ├── aurora.conf.template
│       └── render-mosquitto-config.sh
├── ofsc/
│   └── aurora-agent-ofsc/            # Telegraf agent (host remoto)
└── xiaomi/
    ├── aurora-mobile/                # Telemetry client (Termux)
    └── aurora-mobile-client/         # Voice client (wake word)
```

---

## 🔐 **SECURITY CONSIDERATIONS**

1. **MQTT TLS mutual auth**: Tutti i client autenticati con certificati X.509
2. **Audio encryption**: Audio base64 in MQTT payload (già criptato da TLS)
3. **API authentication**: Data API con token bearer
4. **Command validation**: LLM output validato prima di esecuzione
5. **Rate limiting**: Max 10 comandi vocali/minuto per prevenire abuse
6. **Logging**: Tutti i comandi loggati per audit
7. **Secrets & indirizzi**: Tutti i valori sensibili e gli indirizzi sono in `.env` centrale (non committato); i template usano `envsubst`.

---

## ⚡ **PERFORMANCE TARGETS**

- **Latenza totale**: < 4 secondi (wake word → risposta audio)
- **Whisper STT**: < 2s (con GPU)
- **LLM parsing**: < 500ms
- **Data query**: < 100ms
- **TTS generation**: < 500ms
- **Network latency**: < 200ms (MQTT roundtrip)

---

## 📈 **MONITORING & OBSERVABILITY**

Metriche da tracciare:
- Latenza end-to-end per comando
- Accuracy Whisper (word error rate)
- LLM command parsing success rate
- MQTT message delivery rate
- GPU utilization (workstation)
- Audio quality metrics

Dashboard Grafana dedicata per voice system.

---

# 🎙️ **FOICE ASSISTANT AURORA-LIKE**

Trasformiamo lo Xiaomi in interfaccia vocale per controllare l'infrastruttura.

---

## 🎯 **ARCHITETTURA VOICE ASSISTANT**

```
┌──────────────────────────────────────────────────────────┐
│           WORKSTATION (AI Brain - GPU 4060Ti)            │
│                                                          │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Whisper   │→ │ LLM Command  │→ │ Action Engine   │ │
│  │ (STT GPU)  │  │  Parser      │  │ (MQTT Commands) │ │
│  └────────────┘  └──────────────┘  └─────────────────┘ │
│         ▲                                    │           │
│         │ audio                              │ response  │
│         │                                    ▼           │
│  ┌────────────┐                    ┌─────────────────┐ │
│  │    TTS     │◀───────────────────│  Response Gen   │ │
│  │  (Piper)   │    text response   │  (Ollama/GPT)   │ │
│  └────────────┘                    └─────────────────┘ │
└──────────────────────────────────────────────────────────┘
         ▲                                    │
         │ MQTT audio                         │ MQTT response
         │                                    ▼
┌────────┴────────────────────────────────────────────────┐
│              XIAOMI (Voice Interface)                   │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   Mic   │→ │  Record  │→ │ MQTT Publish Audio   │  │
│  └─────────┘  └──────────┘  └──────────────────────┘  │
│                                                          │
│  ┌──────────────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ MQTT Subscribe   │→ │  Play    │→ │   Speaker    │ │
│  │ Audio Response   │  │  Audio   │  │              │ │
│  └──────────────────┘  └──────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 **PIANO IMPLEMENTAZIONE**

### **STEP 1: Workstation - Setup AI Stack** (30 min)
- Whisper per Speech-to-Text (GPU accelerated)
- Ollama con Llama 3.2 per command parsing
- Piper TTS per risposte vocali
- MQTT bridge per audio streaming

### **STEP 2: Xiaomi - Voice Client** (20 min)
- Termux app con Python
- PyAudio per registrazione
- MQTT client per pub/sub audio
- Audio player per risposte

### **STEP 3: Command Engine** (30 min)
- Parser comandi vocali → azioni MQTT
- Esempi:
  - "Aurora, temperatura server?" → query InfluxDB
  - "Aurora, riavvia gateway" → docker restart
  - "Aurora, CPU workstation?" → real-time stats

---

# 📁 **STRUTTURA COMPLETA FILE SYSTEM - STATO ATTUALE**

---

## 🖥️ **WORKSTATION (${AURORA_WORKSTATION_TS_IP})**

### **Sistema**
- **OS**: Ubuntu (versione da verificare)
- **GPU**: NVIDIA GeForce RTX 4060 Ti 16GB
- **RAM**: 32GB
- **User**: `leoz`

### **Struttura Filesystem**

```
/home/leoz/
│
├── mqtt-certs/                           # Certificati MQTT X.509
│   ├── ca.crt                           # Certificate Authority (2004 bytes)
│   ├── ca.key                           # CA private key
│   ├── ca.srl                           # CA serial
│   ├── broker.crt                       # Broker cert (NON USATO - broker su solidserver)
│   ├── broker.key                       # Broker key (NON USATO)
│   ├── ofsc.crt                         # Client cert per laptop ofsc (1651 bytes)
│   ├── ofsc.key                         # Client key per ofsc (1704 bytes)
│   ├── ofsc.csr                         # Certificate signing request
│   ├── workstation.crt                  # Client cert per workstation (1717 bytes)
│   ├── workstation.key                  # Client key per workstation (1704 bytes)
│   ├── workstation.csr                  # CSR workstation
│   ├── solidserver.crt             # Client cert per solidserver (1651 bytes)
│   ├── solidserver.key             # Client key (1704 bytes)
│   └── solidserver.csr             # CSR solidserver
│
├── aurora-agent-workstation/            # Telegraf Agent per workstation
│   ├── docker-compose.yml               # Container config
│   │   services:
│   │     - telegraf (image: telegraf:1.29-alpine)
│   │       container_name: aurora-agent-workstation
│   │       network_mode: host
│   │
│   ├── telegraf.conf                    # Telegraf configuration
│   │   [agent]
│   │     hostname: ${WORKSTATION_AGENT_TELEGRAF_HOSTNAME}
│   │     interval: 10s
│   │   [[inputs.cpu]]
│   │   [[inputs.mem]]
│   │   [[inputs.disk]]
│   │   [[inputs.system]]
│   │   [[inputs.temp]]
│   │   [[outputs.mqtt]]
│   │     servers: ${WORKSTATION_AGENT_MQTT_URL}
│   │     topic: devices/${WORKSTATION_AGENT_DEVICE_ID}/telemetry
│   │     data_format: influx
│   │     tls_ca: /certs/ca.crt
│   │     tls_cert: /certs/workstation.crt
│   │     tls_key: /certs/workstation.key
│   │
│   ├── telegraf.conf.bak                # Backup config
│   └── certs/                           # Certificati montati in container
│       ├── ca.crt
│       ├── workstation.crt
│       └── workstation.key
│
└── (MQTT Broker rimosso - ora su solidserver)

```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                        STATUS
xxxxxxxxxx     aurora-agent-workstation    Up (running)
```

### **Network Info**
```yaml
Tailscale IP: ${AURORA_WORKSTATION_TS_IP}
Hostname: workstation
Network: Tailscale mesh
```

### **Servizi Attivi**
- Telegraf agent (porta pubblicazione MQTT TLS a solidserver)

---

## 🖥️ **SOLIDSERVER (${AURORA_SOLIDSERVER_TS_IP})**

### **Sistema**
- **OS**: Ubuntu 24.04
- **Hardware**: Server-grade (dettagli da verificare)
- **User**: `leoz`

### **Struttura Filesystem**

```
/home/leoz/
│
├── aurora-edge-hub/                     # Hub centrale IoT
│   ├── docker-compose.yml               # Orchestrazione stack
│   │   version: '3.8'
│   │   networks:
│   │     aurora-net:
│   │   services:
│   │     mosquitto:                     # MQTT Broker
│   │       image: eclipse-mosquitto:2.0
│   │       container_name: aurora-mosquitto
│   │       ports:
│   │         - "1883:1883"              # Non-TLS (local only)
│   │         - "8883:8883"              # TLS (external)
│   │       volumes:
│   │         - /etc/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
│   │         - /etc/mosquitto/conf.d:/mosquitto/config/conf.d
│   │         - /etc/mosquitto/certs:/mosquitto/certs
│   │         - /var/log/mosquitto:/mosquitto/log
│   │       network_mode: host
│   │
│   │     telegraf:                      # Telegraf Centrale
│   │       image: telegraf:1.29-alpine
│   │       container_name: aurora-telegraf
│   │       volumes:
│   │         - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
│   │       network_mode: host
│   │
│   │     influxdb:                      # Time-Series Database
│   │       image: influxdb:2.7-alpine
│   │       container_name: aurora-influxdb
│   │       ports:
│   │         - "${EDGE_INFLUX_BIND_ADDR}:${EDGE_INFLUX_PORT_HOST}:8086"
│   │       volumes:
│   │         - influxdb-data:/var/lib/influxdb2
│   │         - influxdb-config:/etc/influxdb2
│   │       environment:
│   │         DOCKER_INFLUXDB_INIT_MODE: setup
│   │         DOCKER_INFLUXDB_INIT_USERNAME: ${EDGE_INFLUX_INIT_USERNAME}
│   │         DOCKER_INFLUXDB_INIT_PASSWORD: ${EDGE_INFLUX_INIT_PASSWORD}
│   │         DOCKER_INFLUXDB_INIT_ORG: ${EDGE_INFLUX_ORG}
│   │         DOCKER_INFLUXDB_INIT_BUCKET: ${EDGE_INFLUX_BUCKET}
│   │         DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${EDGE_INFLUX_ADMIN_TOKEN}
│   │
│   │     grafana:                       # Dashboard & Visualization
│   │       image: grafana/grafana:10.2.3
│   │       container_name: aurora-grafana
│   │       ports:
│   │         - "${EDGE_GRAFANA_BIND_ADDR}:${EDGE_GRAFANA_PORT_HOST}:3000"
│   │       volumes:
│   │         - grafana-data:/var/lib/grafana
│   │       environment:
│   │         GF_SECURITY_ADMIN_USER: ${EDGE_GRAFANA_ADMIN_USER}
│   │         GF_SECURITY_ADMIN_PASSWORD: ${EDGE_GRAFANA_ADMIN_PASSWORD}
│   │
│   ├── telegraf.conf                    # Telegraf central config
│   │   [agent]
│   │     hostname: ${EDGE_TELEGRAF_HOSTNAME}
│   │     interval: 10s
│   │   [[inputs.mqtt_consumer]]
│   │     servers: ${EDGE_MQTT_URL}
│   │     topics:
│   │       - devices/+/telemetry
│   │       - devices/+/sensors/#
│   │     data_format: influx
│   │   [[processors.regex]]
│   │     [[processors.regex.tags]]
│   │       key: topic
│   │       pattern: ^devices/([^/]+)/.*
│   │       result_key: device
│   │   [[outputs.influxdb_v2]]
│   │     urls: ${EDGE_INFLUX_URL_TELEGRAF}
│   │     token: ${EDGE_INFLUX_ADMIN_TOKEN}
│   │     organization: ${EDGE_INFLUX_ORG}
│   │     bucket: ${EDGE_INFLUX_BUCKET}
│   │
│   └── README.md
│
├── iot-gateway/                         # Gateway locale solidserver
│   ├── docker-compose.yml
│   │   services:
│   │     iot-gateway:
│   │       build: .
│   │       container_name: iot-gateway
│   │       network_mode: host
│   │
│   ├── Dockerfile
│   │   FROM python:3.11-slim
│   │   RUN pip install paho-mqtt psutil pyyaml
│   │   CMD ["python", "/app/app.py"]
│   │
│   ├── app.py                           # Gateway application
│   │   - Legge sensori (temp, CPU) via psutil
│   │   - Pubblica su MQTT in Line Protocol format
│   │   - Topic: ${GATEWAY_MQTT_TELEMETRY_TOPIC}
│   │   - Connessione: ${GATEWAY_MQTT_BROKER_HOST}:${GATEWAY_MQTT_BROKER_PORT} (non-TLS)
│   │   - Intervallo: 6s (configurabile via MQTT command)
│   │
│   ├── app.py.bak                       # Backup versione JSON
│   ├── config/
│   │   └── gateway.yaml
│   │       mqtt:
│   │         broker: ${GATEWAY_MQTT_BROKER_HOST}
│   │         port: ${GATEWAY_MQTT_BROKER_PORT}
│   │         client_id: ${GATEWAY_MQTT_CLIENT_ID}
│   │         topics:
│   │           telemetry: ${GATEWAY_MQTT_TELEMETRY_TOPIC}
│   │           commands: ${GATEWAY_MQTT_COMMANDS_TOPIC}
│   │       sensors:
│   │         temperature:
│   │           interval: 6
│   │       logging:
│   │         level: ${GATEWAY_LOG_LEVEL}
│   │         file: ${GATEWAY_LOG_FILE}
│   │
│   ├── logs/
│   │   └── gateway.log
│   ├── requirements.txt
│   ├── broker.csr
│   ├── broker.key
│   ├── certs/
│   └── README.md
│
├── aurora-agent-solidserver/            # Telegraf Agent solidserver
│   ├── docker-compose.yml
│   │   services:
│   │     telegraf:
│   │       image: telegraf:1.29-alpine
│   │       container_name: aurora-agent-solidserver
│   │       network_mode: host
│   │
│   ├── telegraf.conf
│   │   [agent]
│   │     hostname: ${SOLIDSERVER_AGENT_TELEGRAF_HOSTNAME}
│   │   [[outputs.mqtt]]
│   │     servers: ${SOLIDSERVER_AGENT_MQTT_URL}
│   │     topic: devices/${SOLIDSERVER_AGENT_DEVICE_ID}/telemetry
│   │     data_format: influx
│   │
│   ├── telegraf.conf.bak
│   └── certs/
│       ├── ca.crt
│       ├── solidserver.crt
│       └── solidserver.key
│
└── (altri progetti esistenti)

```

### **System Files**

```
/etc/mosquitto/
├── mosquitto.conf                       # Main config
│   persistence true
│   persistence_location /var/lib/mosquitto/
│   log_dest file /var/log/mosquitto/mosquitto.log
│   log_dest stdout
│   include_dir /etc/mosquitto/conf.d
│
├── conf.d/
│   └── aurora.conf                      # Aurora-specific config
│       # Listener non-TLS (local only)
│       listener ${MOSQUITTO_PLAIN_PORT} ${MOSQUITTO_PLAIN_BIND_ADDR}
│       allow_anonymous true
│       
│       # Listener TLS (external)
│       listener ${MOSQUITTO_TLS_PORT} ${MOSQUITTO_TLS_BIND_ADDR}
│       cafile ${MOSQUITTO_CAFILE}
│       certfile ${MOSQUITTO_CERTFILE}
│       keyfile ${MOSQUITTO_KEYFILE}
│       require_certificate true
│       use_identity_as_username true
│       allow_anonymous false
│
└── certs/
    ├── ca.crt                           # CA certificate
    ├── broker.crt                       # Broker cert (CN=${AURORA_SOLIDSERVER_TS_IP})
    └── broker.key                       # Broker private key
    Permissions: mosquitto:mosquitto, 644 for .crt, 600 for .key

/var/log/mosquitto/
└── mosquitto.log                        # Broker logs
```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                        STATUS
xxxxxxxxxx     aurora-mosquitto            Up
xxxxxxxxxx     aurora-telegraf             Up
xxxxxxxxxx     aurora-influxdb             Up (port 8086)
xxxxxxxxxx     aurora-grafana              Up (port 3001)
xxxxxxxxxx     iot-gateway                 Up
xxxxxxxxxx     aurora-agent-solidserver    Up
```

### **InfluxDB Data**
```yaml
Organization: ${EDGE_INFLUX_ORG}
Bucket: telemetry
  - Retention: infinite
  - ID: 94499a39ccb4a7ee

Tokens:
  - ${EDGE_INFLUX_ADMIN_TOKEN} (admin, all permissions)
  - RraCDJ7ol071KAl1Y9e39BK89iUSA75hok4qg3KbS3Cux_uOgejFmcbLmQu7VVfU_L6qC7c4-eVVToIBpgBGGA== (read bucket 1034f0cdf394b000)
  - dheEEzcWI0VjA1_JQBC60-Z91YupfxjgtUymrmR8Bqr8DhraosxeMiTKFCN7u2Tq2mFjnUV2i3WitI4x0c6tbQ== (read telemetry bucket)

Measurements:
  - cpu (from all agents)
  - mem (from all agents)
  - disk (from all agents)
  - system (from all agents)
  - temp (from all agents)
  - sensors (from gateway solidserver)
  - mobile_battery (from xiaomi)
  - mobile_telemetry (from xiaomi)

Devices:
  - ofsc
  - workstation
  - solidserver
  - mobile-xiaomi
```

### **Grafana**
```yaml
URL: http://${AURORA_SOLIDSERVER_TS_IP}:3001 (MagicDNS: http://solidserver:3001/)
Credentials:
  - Username: ${EDGE_GRAFANA_ADMIN_USER}
  - Password: ${EDGE_GRAFANA_ADMIN_PASSWORD}

Data Sources:
  - InfluxDB-Telemetry
    URL: ${EDGE_INFLUX_URL_GRAFANA}
    Token: ${EDGE_INFLUX_ADMIN_TOKEN}
    Organization: ${EDGE_INFLUX_ORG}
    Bucket: ${EDGE_INFLUX_BUCKET}

Dashboards:
  - Aurora Overview
  - Aurora Device Detail
```

### **Network Info**
```yaml
Tailscale IP: ${AURORA_SOLIDSERVER_TS_IP}
Hostname: solidserver
Services:
  - Mosquitto: 1883 (local only), 8883 (TLS all interfaces)
  - InfluxDB: 8086
  - Grafana: 3001
```

---

## 💻 **LAPTOP OFSC (${AURORA_OFSC_TS_IP})**

### **Sistema**
- **OS**: Ubuntu (fascia bassa)
- **User**: `user`

### **Struttura Filesystem**

```
/home/user/
│
└── aurora-agent-ofsc/                   # Telegraf Agent
    ├── docker-compose.yml
    │   version: '3.8'
    │   services:
    │     telegraf:
    │       image: telegraf:1.29-alpine
    │       container_name: aurora-agent-ofsc
    │       network_mode: host
    │
    ├── telegraf.conf
    │   [agent]
    │     hostname: ${OFSC_AGENT_TELEGRAF_HOSTNAME}
    │     interval: 10s
    │   [[inputs.cpu]]
    │   [[inputs.mem]]
    │   [[inputs.disk]]
    │   [[inputs.system]]
    │   [[inputs.temp]]
    │   [[outputs.mqtt]]
    │     servers: ${OFSC_AGENT_MQTT_URL}
    │     topic: devices/${OFSC_AGENT_DEVICE_ID}/telemetry
    │     client_id: ${OFSC_AGENT_DEVICE_ID}-telegraf
    │     data_format: influx
    │     tls_ca: /certs/ca.crt
    │     tls_cert: /certs/ofsc.crt
    │     tls_key: /certs/ofsc.key
    │
    ├── telegraf.conf.bak
    └── certs/
        ├── ca.crt                       # 2004 bytes
        ├── ofsc.crt                     # 1651 bytes
        └── ofsc.key                     # 1704 bytes
```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                STATUS
xxxxxxxxxx     aurora-agent-ofsc   Up
```

### **Docker Setup**
- User aggiunto a gruppo docker: `usermod -aG docker user`
- Permessi corretti applicati

### **Network Info**
```yaml
Tailscale IP: ${AURORA_OFSC_TS_IP}
Hostname: ofsc
```

---

## 📱 **XIAOMI (${AURORA_XIAOMI_TS_IP})**

### **Sistema**
- **OS**: Android + Termux
- **App**: Termux (terminal Linux su Android)

### **Struttura Filesystem**

```
/data/data/com.termux/files/home/
│
└── aurora-mobile/                       # Client MQTT telemetria mobile
    ├── config.yaml
    │   mqtt:
    │     broker: ${XIAOMI_MQTT_BROKER_HOST}
    │     port: ${XIAOMI_MQTT_BROKER_PORT}
    │     client_id: ${XIAOMI_MQTT_CLIENT_ID}
    │     username: ${XIAOMI_MQTT_USERNAME}
    │     password: ${XIAOMI_MQTT_PASSWORD}
    │     topics:
    │       telemetry: ${XIAOMI_MQTT_TELEMETRY_TOPIC}
    │       commands: ${XIAOMI_MQTT_COMMANDS_TOPIC}
    │       sensors:
    │         battery: ${XIAOMI_MQTT_SENSORS_BATTERY_TOPIC}
    │         location: ${XIAOMI_MQTT_SENSORS_LOCATION_TOPIC}
    │         sensor: ${XIAOMI_MQTT_SENSORS_SENSOR_TOPIC}
    │   sensors:
    │     interval: ${XIAOMI_SENSORS_INTERVAL}
    │   logging:
    │     level: INFO
    │
    ├── mobile_sensors.py                # MQTT + Termux sensors + comandi
    │   - Legge batteria via Termux API
    │   - Pubblica Influx line protocol:
    │     - mobile_battery (sensors/battery)
    │     - mobile_telemetry (telemetry)
    │   - Sottoscrive ${XIAOMI_MQTT_COMMANDS_TOPIC}
    │
    └── certs/
        ├── ca.crt
        ├── mobile.crt                   # Certificato client
        └── mobile.key
```

### **Termux Packages Installati**
```bash
- python (3.11)
- termux-api (per accesso sensori Android)
- openssl (per TLS)
```

### **Python Packages**
```bash
- paho-mqtt
- pyyaml
```

### **Stato Client**
```yaml
Status: Gestito da Termux Boot (start-aurora.sh)
MQTT Connection:
  - Broker: ${XIAOMI_MQTT_BROKER_HOST}:${XIAOMI_MQTT_BROKER_PORT}
  - TLS: enabled
  - Authentication: X.509 certificate (CN=mobile-xiaomi)
  - Connected: Yes (log mosquitto mostra "New client connected from ${AURORA_XIAOMI_TS_IP}")
```

### **Network Info**
```yaml
Tailscale IP: ${AURORA_XIAOMI_TS_IP}
Hostname: xiaomi (o simile)
Connection: Mobile (LTE/WiFi via Tailscale)
```

---

## 🔐 **CERTIFICATI X.509 - RIEPILOGO**

### **Certificate Authority (CA)**
```yaml
Location: workstation:~/mqtt-certs/ca.crt
  - Common Name: Aurora Lab CA
  - Valid: 365 days
  - Used by: tutti i client per verificare broker e peers
```

### **Broker Certificate**
```yaml
Location: solidserver:/etc/mosquitto/certs/broker.crt
  - Common Name: ${AURORA_SOLIDSERVER_TS_IP}
  - SAN: IP:${AURORA_SOLIDSERVER_TS_IP}
  - Used by: Mosquitto broker su porta 8883
```

### **Client Certificates**
```yaml
1. ofsc
   Location: ofsc:~/aurora-agent-ofsc/certs/ofsc.crt
   CN: ofsc
   Used by: Telegraf agent ofsc
   MQTT username: ofsc (from CN)

2. workstation
   Location: workstation:~/aurora-agent-workstation/certs/workstation.crt
   CN: workstation
   Used by: Telegraf agent workstation
   MQTT username: workstation

3. solidserver
   Location: solidserver:~/aurora-agent-solidserver/certs/solidserver.crt
   CN: solidserver
   Used by: Telegraf agent solidserver
   MQTT username: solidserver

4. mobile (xiaomi)
   Location: xiaomi:~/aurora-mobile/certs/mobile.crt
   CN: mobile-xiaomi
   Used by: Python MQTT client su Xiaomi
   MQTT username: mobile-xiaomi
```

---

## 📊 **MQTT TOPICS - STATO ATTUALE**

```
devices/
├── ofsc/
│   └── telemetry                        # Line Protocol (Telegraf)
│       Frequency: 10s
│       Measurements: cpu, mem, disk, system, temp
│
├── workstation/
│   └── telemetry                        # Line Protocol (Telegraf)
│       Frequency: 10s
│       Measurements: cpu, mem, disk, system, temp
│
├── solidserver/
│   ├── telemetry                        # Line Protocol (Telegraf + Gateway)
│   │   Frequency: 6-10s
│   │   Measurements: cpu, mem, disk, system, temp, sensors
│   └── commands                         # Commands to gateway
│       Payload: {"action": "set_interval", "value": X}
│
└── mobile-xiaomi/
    ├── sensors/
    │   └── battery                      # Line Protocol (mobile_battery)
    │       Frequency: 10s
    │       Measurements: percentage, temperature
    └── telemetry                        # Line Protocol (mobile_telemetry + system)
        Frequency: 10s
        Measurements:
          - mobile_telemetry: iteration, battery_percent, battery_temp
          - cpu: usage_active
          - mem: used_percent
          - disk: used_percent (tag: path)
          - system: uptime, load1
          - temp: temp (tag: sensor=battery)
```

---

## 🌐 **NETWORK TOPOLOGY**

```
Tailscale Mesh Network (100.x.x.x/10)
│
├── ${AURORA_WORKSTATION_TS_IP} (workstation)
│   Services: Telegraf Agent
│   Outbound: MQTT TLS → solidserver:8883
│
├── ${AURORA_SOLIDSERVER_TS_IP} (solidserver)
│   Services:
│     - Mosquitto MQTT Broker (1883 local, 8883 TLS)
│     - InfluxDB (8086)
│     - Grafana (3001)
│     - Telegraf Central (consume MQTT → InfluxDB)
│     - Gateway (publish sensors)
│     - Telegraf Agent (publish metrics)
│   Inbound:
│     - MQTT TLS 8883 ← all devices
│     - HTTP 8086 ← Grafana
│     - HTTP 3001 ← users
│
├── ${AURORA_OFSC_TS_IP} (ofsc)
│   Services: Telegraf Agent
│   Outbound: MQTT TLS → solidserver:8883
│
└── ${AURORA_XIAOMI_TS_IP} (xiaomi)
    Services: Python MQTT Client
    Outbound: MQTT TLS → solidserver:8883
```

---

## 📦 **VOLUMI DOCKER**

### **Solidserver**
```yaml
Volumes:
  - influxdb-data: /var/lib/docker/volumes/aurora-edge-hub_influxdb-data
    Size: ~varios MB (time-series data)
    Contains: InfluxDB bucket data
  
  - influxdb-config: /var/lib/docker/volumes/aurora-edge-hub_influxdb-config
    Contains: InfluxDB configuration
  
  - grafana-data: /var/lib/docker/volumes/aurora-edge-hub_grafana-data
    Contains: Grafana dashboards, users, datasources
```

---

## 🔍 **COMANDI UTILI PER VERIFICA**

### **Workstation**
```bash
# Verifica agent
sudo docker ps | grep workstation
sudo docker logs aurora-agent-workstation --tail=20

# Verifica certificati
ls -lh ~/mqtt-certs/
openssl x509 -in ~/mqtt-certs/workstation.crt -text -noout
```

### **Solidserver**
```bash
# Verifica stack
cd ~/aurora-edge-hub
docker compose ps
docker compose logs -f

# Verifica Mosquitto
sudo tail -f /var/log/mosquitto/mosquitto.log
mosquitto_sub -h ${AURORA_SOLIDSERVER_TS_IP} -p 1883 -t "devices/#" -v

# Verifica InfluxDB
docker exec -it aurora-influxdb influx bucket list --org ${EDGE_INFLUX_ORG}
docker exec -it aurora-influxdb influx query 'from(bucket:"telemetry") |> range(start:-5m) |> limit(n:10)' --org ${EDGE_INFLUX_ORG} --token ${EDGE_INFLUX_ADMIN_TOKEN}

# Verifica certificati broker
ls -lh /etc/mosquitto/certs/
sudo openssl x509 -in /etc/mosquitto/certs/broker.crt -text -noout
```

### **OFSC**
```bash
# Verifica agent
docker ps | grep ofsc
docker logs aurora-agent-ofsc --tail=20
```

### **Xiaomi (Termux)**
```bash
# Verifica processo
ps aux | grep mqtt
# Verifica log (se loggato)
tail -f ~/aurora-mobile/mqtt.log
```

---

**Questa è la struttura completa e attuale. Vuoi che procediamo con l'implementazione del voice assistant o hai bisogno di altre verifiche?**
