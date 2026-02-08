# 🎙️ **DESIGN COMPLETO: ATLAS VOICE ASSISTANT**

---

## 📐 **ARCHITETTURA DETTAGLIATA**

### **1. COMPONENTI SISTEMA**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ATLAS-LAB (Central Brain)                          │
│                    ${ATLAS_LAB_TS_IP} - Ubuntu + GPU 4060Ti                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              CONTAINER: atlas-voice-engine                      │ │
│  │  Port: 8000 (API), Network: atlas-net                          │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │  1. MQTT Subscriber (voice/+/audio/request)                     │ │
│  │     ↓ riceve audio Base64 da Atlas Mobile                             │ │
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
│  │     ↓ invia audio Base64 a Atlas Mobile                               │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              CONTAINER: atlas-ollama                            │ │
│  │  Port: 11434, GPU: enabled, Model: llama3.2:3b                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              EXISTING: Mosquitto MQTT Broker                     │ │
│  │  Port: 1883 (local), 8883 (TLS)                                 │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    ATLAS-CORE (Edge Hub)                               │
│                    ${ATLAS_CORE_TS_IP} - Ubuntu 24.04                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  EXISTING: InfluxDB + Telegraf + Grafana                         │ │
│  │  - Fornisce dati per query vocali                               │ │
│  │  - Endpoint: ${EDGE_INFLUX_URL_TELEGRAF} (InfluxDB)             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  NUOVO: atlas-data-api                                          │ │
│  │  Port: 8001                                                      │ │
│  │  - REST API per query InfluxDB semplificate                     │ │
│  │  - Endpoints: /metrics/{device}/{type}                          │ │
│  │  - Cache 5s per ridurre latenza                                 │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    ATLAS-MOBILE (Voice Interface)                             │
│                    ${ATLAS_MOBILE_TS_IP} - Android + Termux                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │              atlas-mobile-client.py                             │ │
│  │  Python 3.11 in Termux                                           │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │  1. Wake Word Detection (PocketSphinx)                           │ │
│  │     Keyword: "Atlas" o "Hey Atlas"                            │ │
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
│  │     Topic: voice/atlas-mobile/audio/request                           │ │
│  │     Payload: {audio: "base64...", user_id: "atlas-mobile"}           │ │
│  │     QoS: 1, TLS: enabled                                         │ │
│  │                                                                  │ │
│  │  5. MQTT Subscriber                                              │ │
│  │     Topic: voice/atlas-mobile/audio/response                          │ │
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
   "Atlas, qual è la temperatura del server?"
   
   ↓ [Atlas Mobile mic]
   
2. WAKE WORD DETECTION
   Keyword "Atlas" detected → START recording
   
   ↓ [Record 5s audio]
   
3. ENCODE & PUBLISH
   audio.wav → base64 → MQTT
   Topic: voice/atlas-mobile/audio/request
   
   ↓ [MQTTS over Tailscale]
   
4. ATLAS-LAB RICEVE
   atlas-voice-engine subscribe
   
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
     "target": "atlas-core",
     "metric": "temperature",
     "action": "get_current_value"
   }
   """
   Tempo: ~500ms
   
   ↓ [Structured command]
   
7. ACTION EXECUTION
   a) Query InfluxDB via REST API:
      GET http://${ATLAS_CORE_TS_IP}:8001/metrics/atlas-core/temperature
      
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
    Topic: voice/atlas-mobile/audio/response
    Payload: {
      "audio": "base64...",
      "text": "La temperatura del server...",
      "metadata": {...}
    }
    
    ↓ [MQTTS over Tailscale]
    
11. ATLAS-MOBILE RICEVE
    atlas-mobile-client subscribe
    
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
atlas/
├── voice/
│   ├── atlas-mobile/
│   │   ├── audio/
│   │   │   ├── request          # Atlas Mobile → Atlas Lab (audio queries)
│   │   │   └── response         # Atlas Lab → Atlas Mobile (audio replies)
│   │   ├── status               # Atlas Mobile status (online/offline)
│   │   └── config               # Runtime config updates
│   │
│   └── commands/                # Direct commands (non-voice)
│       ├── restart/+
│       ├── status/+
│       └── action/+
│
├── devices/
│   ├── atlas-mobile/
│   │   ├── telemetry            # EXISTING: battery, sensors
│   │   └── sensors/#
│   │
│   ├── atlas-field/telemetry           # EXISTING: system metrics
│   ├── atlas-lab/telemetry    # EXISTING: system metrics
│   └── atlas-core/telemetry    # system metrics + gateway sensors
│
└── system/
    ├── alerts/#                 # System-wide alerts
    ├── health/#                 # Health checks
    └── logs/#                   # Centralized logging
```

---

## 🗄️ **DATI NECESSARI PER INTEGRAZIONE**

### **A. MQTT Broker (Atlas Lab)**
```yaml
Broker:
  Host: ${ATLAS_LAB_TS_IP}
  Port TLS: 8883
  Port Local: 1883
  
Certificati esistenti:
  - CA: ~/mqtt-certs/ca.crt
  - Atlas Lab: ~/mqtt-certs/atlas-lab.{crt,key}
  
Nuovi certificati da generare:
  - atlas-engine: per voice-engine container
  - atlas-mobile-voice: per client vocale (separato da atlas-mobile telemetria)

Topics da sottoscrivere (voice-engine):
  - voice/+/audio/request
  - atlas/commands/#
  
Topics da pubblicare (voice-engine):
  - voice/+/audio/response
  - atlas/system/alerts/#
```

### **B. InfluxDB (Atlas Core)**
```yaml
Database:
  Host: ${ATLAS_CORE_TS_IP}:8086
  Org: ${EDGE_INFLUX_ORG}
  Bucket: telemetry
  Token: ${EDGE_INFLUX_GRAFANA_TOKEN} (read)
  
Measurements disponibili:
  - cpu (fields: usage_active, usage_idle, ...)
  - mem (fields: used_percent, available, ...)
  - disk (fields: used_percent, free, ...)
  - temp (fields: temp, sensor tag)
  - system (fields: load1, load5, load15, uptime)
  - sensors (device=atlas-core: temperature, cpu_usage)

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

### **C. Docker Networks (Atlas Lab)**
```yaml
Network: bridge (default)
  - atlas-voice-engine
  - atlas-ollama
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

### **D. Atlas Mobile (Termux)**
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
  - ca.crt: ~/atlas-mobile/certs/
  - atlas-mobile-voice.crt
  - atlas-mobile-voice.key

Config file: ~/atlas-mobile/config.yaml
  mqtt:
    broker: ${ATLAS_LAB_TS_IP}
    port: 8883
    client_id: ${ATLAS_MOBILE_VOICE_CLIENT_ID}
    username: ${ATLAS_MOBILE_VOICE_USERNAME}
  audio:
    wake_word: atlas
    sample_rate: 16000
    channels: 1
    record_duration: 5
```

---

## 🎯 **COMANDI VOCALI SUPPORTATI (MVP)**

### **1. QUERY METRICHE**
```
"Atlas, temperatura del server"
"Atlas, quanta CPU sta usando atlas-lab"
"Atlas, memoria disponibile su atlas-field"
"Atlas, carico sistema atlas-core"
"Atlas, spazio disco atlas-lab"
"Atlas, uptime di tutti i device"
```

### **2. CONTROLLO DISPOSITIVI**
```
"Atlas, riavvia gateway"
"Atlas, stato container su atlas-core"
"Atlas, spegni Grafana"
"Atlas, avvia InfluxDB"
```

### **3. INFORMAZIONI SISTEMA**
```
"Atlas, quanti device sono online"
"Atlas, mostrami gli alert attivi"
"Atlas, quando è stato l'ultimo backup"
"Atlas, connessione MQTT funziona"
```

### **4. AUTOMAZIONI**
```
"Atlas, notificami se CPU supera 80%"
"Atlas, crea report giornaliero temperature"
"Atlas, alert se disco < 10GB"
```

---

## 📦 **FILE STRUCTURE PROGETTO**

```
~/atlas-infra/
├── atlas-lab/
│   └── atlas-agent-lab/
│       ├── docker-compose.yml
│       ├── telegraf.conf
│       └── certs/
├── atlas-core/
│   ├── edge-hub/
│   │   ├── docker-compose.yml
│   │   ├── telegraf.conf.template
│   │   ├── provisioning/
│   │   └── render-runtime-config.sh
│   ├── atlas-agent-core/
│   │   ├── docker-compose.yml
│   │   ├── telegraf.conf.template
│   │   └── render-runtime-config.sh
│   ├── iot-gateway/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── config/
│   └── mosquitto/
│       ├── atlas.conf.template
│       └── render-mosquitto-config.sh
├── atlas-field/
│   └── atlas-agent-field/            # Telegraf agent (host remoto)
└── atlas-mobile/
    ├── atlas-mobile/                # Telemetry client (Termux)
    └── atlas-mobile-client/         # Voice client (wake word)
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
8. **Least privilege**: Token Influx separati (read/write) e ACL MQTT opzionali per topic.

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
- GPU utilization (atlas-lab)
- Audio quality metrics

Dashboard Grafana dedicata per voice system.

---

# 🎙️ **FOICE ASSISTANT ATLAS-LIKE**

Trasformiamo lo Atlas Mobile in interfaccia vocale per controllare l'infrastruttura.

---

## 🎯 **ARCHITETTURA VOICE ASSISTANT**

```
┌──────────────────────────────────────────────────────────┐
│           ATLAS-LAB (AI Brain - GPU 4060Ti)            │
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
│              ATLAS-MOBILE (Voice Interface)                   │
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

### **STEP 1: Atlas Lab - Setup AI Stack** (30 min)
- Whisper per Speech-to-Text (GPU accelerated)
- Ollama con Llama 3.2 per command parsing
- Piper TTS per risposte vocali
- MQTT bridge per audio streaming

### **STEP 2: Atlas Mobile - Voice Client** (20 min)
- Termux app con Python
- PyAudio per registrazione
- MQTT client per pub/sub audio
- Audio player per risposte

### **STEP 3: Command Engine** (30 min)
- Parser comandi vocali → azioni MQTT
- Esempi:
  - "Atlas, temperatura server?" → query InfluxDB
  - "Atlas, riavvia gateway" → docker restart
  - "Atlas, CPU atlas-lab?" → real-time stats

---

# 📁 **STRUTTURA COMPLETA FILE SYSTEM - STATO ATTUALE**

---

## 🖥️ **ATLAS-LAB (${ATLAS_LAB_TS_IP})**

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
│   ├── broker.crt                       # Broker cert (NON USATO - broker su atlas-core)
│   ├── broker.key                       # Broker key (NON USATO)
│   ├── atlas-field.crt                         # Client cert per laptop atlas-field (1651 bytes)
│   ├── atlas-field.key                         # Client key per atlas-field (1704 bytes)
│   ├── atlas-field.csr                         # Certificate signing request
│   ├── atlas-lab.crt                  # Client cert per atlas-lab (1717 bytes)
│   ├── atlas-lab.key                  # Client key per atlas-lab (1704 bytes)
│   ├── atlas-lab.csr                  # CSR atlas-lab
│   ├── atlas-core.crt             # Client cert per atlas-core (1651 bytes)
│   ├── atlas-core.key             # Client key (1704 bytes)
│   └── atlas-core.csr             # CSR atlas-core
│
├── atlas-agent-lab/            # Telegraf Agent per atlas-lab
│   ├── docker-compose.yml               # Container config
│   │   services:
│   │     - telegraf (image: telegraf:1.29-alpine)
│   │       container_name: atlas-agent-lab
│   │       network_mode: host
│   │
│   ├── telegraf.conf                    # Telegraf configuration
│   │   [agent]
│   │     hostname: ${ATLAS_LAB_AGENT_TELEGRAF_HOSTNAME}
│   │     interval: 10s
│   │   [[inputs.cpu]]
│   │   [[inputs.mem]]
│   │   [[inputs.disk]]
│   │   [[inputs.system]]
│   │   [[inputs.temp]]
│   │   [[outputs.mqtt]]
│   │     servers: ${ATLAS_LAB_AGENT_MQTT_URL}
│   │     topic: devices/${ATLAS_LAB_AGENT_DEVICE_ID}/telemetry
│   │     data_format: influx
│   │     tls_ca: /certs/ca.crt
│   │     tls_cert: /certs/atlas-lab.crt
│   │     tls_key: /certs/atlas-lab.key
│   │
│   ├── telegraf.conf.bak                # Backup config
│   └── certs/                           # Certificati montati in container
│       ├── ca.crt
│       ├── atlas-lab.crt
│       └── atlas-lab.key
│
└── (MQTT Broker rimosso - ora su atlas-core)

```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                        STATUS
xxxxxxxxxx     atlas-agent-lab    Up (running)
```

### **Network Info**
```yaml
Tailscale IP: ${ATLAS_LAB_TS_IP}
Hostname: atlas-lab
Network: Tailscale mesh
```

### **Servizi Attivi**
- Telegraf agent (porta pubblicazione MQTT TLS a atlas-core)

---

## 🖥️ **ATLAS-CORE (${ATLAS_CORE_TS_IP})**

### **Sistema**
- **OS**: Ubuntu 24.04
- **Hardware**: Server-grade (dettagli da verificare)
- **User**: `leoz`

### **Struttura Filesystem**

```
/home/leoz/
│
├── atlas-infra/atlas-core/edge-hub/     # Hub centrale IoT
│   ├── docker-compose.yml               # InfluxDB + Grafana + Telegraf collector
│   │   version: '3.8'
│   │   services:
│   │     influxdb:
│   │     telegraf:
│   │     grafana:
│   │   # Mosquitto gira via systemd (non in docker-compose)
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
│   │     token: ${EDGE_INFLUX_TELEGRAF_TOKEN}
│   │     organization: ${EDGE_INFLUX_ORG}
│   │     bucket: ${EDGE_INFLUX_BUCKET}
│   │
│   └── README.md
│
├── iot-gateway/                         # Gateway locale atlas-core
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
├── atlas-agent-core/            # Telegraf Agent atlas-core
│   ├── docker-compose.yml
│   │   services:
│   │     telegraf:
│   │       image: telegraf:1.29-alpine
│   │       container_name: atlas-agent-core
│   │       network_mode: host
│   │
│   ├── telegraf.conf
│   │   [agent]
│   │     hostname: ${ATLAS_CORE_AGENT_TELEGRAF_HOSTNAME}
│   │   [[outputs.mqtt]]
│   │     servers: ${ATLAS_CORE_AGENT_MQTT_URL}
│   │     topic: devices/${ATLAS_CORE_AGENT_DEVICE_ID}/telemetry
│   │     data_format: influx
│   │
│   ├── telegraf.conf.bak
│   └── certs/
│       ├── ca.crt
│       ├── atlas-core.crt
│       └── atlas-core.key
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
│   └── atlas.conf                      # Atlas-specific config
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
│       acl_file ${MOSQUITTO_ACL_FILE}  # optional
│
└── certs/
    ├── ca.crt                           # CA certificate
    ├── broker.crt                       # Broker cert (CN=${ATLAS_CORE_TS_IP})
    └── broker.key                       # Broker private key
    Permissions: mosquitto:mosquitto, 644 for .crt, 600 for .key

/var/log/mosquitto/
└── mosquitto.log                        # Broker logs
```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                        STATUS
# mosquitto e gestito via systemd (non container)
xxxxxxxxxx     edge-hub-telegraf-1         Up
xxxxxxxxxx     edge-hub-influxdb-1         Up (port 8086)
xxxxxxxxxx     edge-hub-grafana-1          Up (port 3001)
xxxxxxxxxx     iot-gateway                 Up (optional)
xxxxxxxxxx     atlas-agent-core            Up
```

### **InfluxDB Data**
```yaml
Organization: ${EDGE_INFLUX_ORG}
Bucket: telemetry
  - Retention: infinite
  - ID: 94499a39ccb4a7ee

Tokens:
  - ${EDGE_INFLUX_ADMIN_TOKEN} (admin, bootstrap only)
  - ${EDGE_INFLUX_TELEGRAF_TOKEN} (write: telemetry)
  - ${EDGE_INFLUX_GRAFANA_TOKEN} (read: telemetry)

Measurements:
  - cpu (from all agents)
  - mem (from all agents)
  - disk (from all agents)
  - system (from all agents)
  - temp (from all agents)
  - sensors (from gateway atlas-core)
  - mobile_battery (from atlas-mobile)
  - mobile_telemetry (from atlas-mobile)

Devices:
  - atlas-field
  - atlas-lab
  - atlas-core
  - atlas-mobile
```

### **Grafana**
```yaml
URL: http://${ATLAS_CORE_TS_IP}:3001 (MagicDNS: http://atlas-core:3001/)
Credentials:
  - Username: ${EDGE_GRAFANA_ADMIN_USER}
  - Password: ${EDGE_GRAFANA_ADMIN_PASSWORD}

Data Sources:
  - InfluxDB-Telemetry
    URL: ${EDGE_INFLUX_URL_GRAFANA}
    Token: ${EDGE_INFLUX_GRAFANA_TOKEN}
    Organization: ${EDGE_INFLUX_ORG}
    Bucket: ${EDGE_INFLUX_BUCKET}

Dashboards:
  - Atlas Overview
  - Atlas Device Detail
```

### **Network Info**
```yaml
Tailscale IP: ${ATLAS_CORE_TS_IP}
Hostname: atlas-core
Services:
  - Mosquitto: 1883 (local only), 8883 (TLS all interfaces)
  - InfluxDB: 8086
  - Grafana: 3001
```

---

## 💻 **LAPTOP ATLAS-FIELD (${ATLAS_FIELD_TS_IP})**

### **Sistema**
- **OS**: Ubuntu (fascia bassa)
- **User**: `user`

### **Struttura Filesystem**

```
/home/user/
│
└── atlas-agent-field/                   # Telegraf Agent
    ├── docker-compose.yml
    │   version: '3.8'
    │   services:
    │     telegraf:
    │       image: telegraf:1.29-alpine
    │       container_name: atlas-agent-field
    │       network_mode: host
    │
    ├── telegraf.conf
    │   [agent]
    │     hostname: ${ATLAS_FIELD_AGENT_TELEGRAF_HOSTNAME}
    │     interval: 10s
    │   [[inputs.cpu]]
    │   [[inputs.mem]]
    │   [[inputs.disk]]
    │   [[inputs.system]]
    │   [[inputs.temp]]
    │   [[outputs.mqtt]]
    │     servers: ${ATLAS_FIELD_AGENT_MQTT_URL}
    │     topic: devices/${ATLAS_FIELD_AGENT_DEVICE_ID}/telemetry
    │     client_id: ${ATLAS_FIELD_AGENT_DEVICE_ID}-telegraf
    │     data_format: influx
    │     tls_ca: /certs/ca.crt
    │     tls_cert: /certs/atlas-field.crt
    │     tls_key: /certs/atlas-field.key
    │
    ├── telegraf.conf.bak
    └── certs/
        ├── ca.crt                       # 2004 bytes
        ├── atlas-field.crt                     # 1651 bytes
        └── atlas-field.key                     # 1704 bytes
```

### **Container Docker Attivi**
```bash
CONTAINER ID   NAME                STATUS
xxxxxxxxxx     atlas-agent-field   Up
```

### **Docker Setup**
- User aggiunto a gruppo docker: `usermod -aG docker user`
- Permessi corretti applicati

### **Network Info**
```yaml
Tailscale IP: ${ATLAS_FIELD_TS_IP}
Hostname: atlas-field
```

---

## 📱 **ATLAS-MOBILE (${ATLAS_MOBILE_TS_IP})**

### **Sistema**
- **OS**: Android + Termux
- **App**: Termux (terminal Linux su Android)

### **Struttura Filesystem**

```
/data/data/com.termux/files/home/
│
└── atlas-mobile/                       # Client MQTT telemetria mobile
    ├── config.yaml
    │   mqtt:
    │     broker: ${ATLAS_MOBILE_MQTT_BROKER_HOST}
    │     port: ${ATLAS_MOBILE_MQTT_BROKER_PORT}
    │     client_id: ${ATLAS_MOBILE_MQTT_CLIENT_ID}
    │     username: ${ATLAS_MOBILE_MQTT_USERNAME}
    │     password: ${ATLAS_MOBILE_MQTT_PASSWORD}
    │     topics:
    │       telemetry: ${ATLAS_MOBILE_MQTT_TELEMETRY_TOPIC}
    │       commands: ${ATLAS_MOBILE_MQTT_COMMANDS_TOPIC}
    │       sensors:
    │         battery: ${ATLAS_MOBILE_MQTT_SENSORS_BATTERY_TOPIC}
    │         location: ${ATLAS_MOBILE_MQTT_SENSORS_LOCATION_TOPIC}
    │         sensor: ${ATLAS_MOBILE_MQTT_SENSORS_SENSOR_TOPIC}
    │   sensors:
    │     interval: ${ATLAS_MOBILE_SENSORS_INTERVAL}
    │   logging:
    │     level: INFO
    │
    ├── mobile_sensors.py                # MQTT + Termux sensors + comandi
    │   - Legge batteria via Termux API
    │   - Pubblica Influx line protocol:
    │     - mobile_battery (sensors/battery)
    │     - mobile_telemetry (telemetry)
    │   - Sottoscrive ${ATLAS_MOBILE_MQTT_COMMANDS_TOPIC}
    │
    └── certs/
        ├── ca.crt
        ├── atlas-mobile.crt             # Certificato client
        └── atlas-mobile.key
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
Status: Gestito da Termux Boot (start-atlas.sh)
MQTT Connection:
  - Broker: ${ATLAS_MOBILE_MQTT_BROKER_HOST}:${ATLAS_MOBILE_MQTT_BROKER_PORT}
  - TLS: enabled
  - Authentication: X.509 certificate (CN=atlas-mobile)
  - Connected: Yes (log mosquitto mostra "New client connected from ${ATLAS_MOBILE_TS_IP}")
```

### **Network Info**
```yaml
Tailscale IP: ${ATLAS_MOBILE_TS_IP}
Hostname: atlas-mobile (o simile)
Connection: Mobile (LTE/WiFi via Tailscale)
```

---

## 🔐 **CERTIFICATI X.509 - RIEPILOGO**

### **Certificate Authority (CA)**
```yaml
Location: atlas-lab:~/mqtt-certs/ca.crt
  - Common Name: Atlas Lab CA
  - Valid: 365 days
  - Used by: tutti i client per verificare broker e peers
```

### **Broker Certificate**
```yaml
Location: atlas-core:/etc/mosquitto/certs/broker.crt
  - Common Name: ${ATLAS_CORE_TS_IP}
  - SAN: IP:${ATLAS_CORE_TS_IP}
  - Used by: Mosquitto broker su porta 8883
```

### **Client Certificates**
```yaml
1. atlas-field
   Location: atlas-field:~/atlas-agent-field/certs/atlas-field.crt
   CN: atlas-field
   Used by: Telegraf agent atlas-field
   MQTT username: atlas-field (from CN)

2. atlas-lab
   Location: atlas-lab:~/atlas-agent-lab/certs/atlas-lab.crt
   CN: atlas-lab
   Used by: Telegraf agent atlas-lab
   MQTT username: atlas-lab

3. atlas-core
   Location: atlas-core:~/atlas-agent-core/certs/atlas-core.crt
   CN: atlas-core
   Used by: Telegraf agent atlas-core
   MQTT username: atlas-core

4. mobile (atlas-mobile)
   Location: atlas-mobile:~/atlas-mobile/certs/atlas-mobile.crt
   CN: atlas-mobile
   Used by: Python MQTT client su Atlas Mobile
   MQTT username: atlas-mobile
```

---

## 📊 **MQTT TOPICS - STATO ATTUALE**

```
devices/
├── atlas-field/
│   └── telemetry                        # Line Protocol (Telegraf)
│       Frequency: 10s
│       Measurements: cpu, mem, disk, system, temp
│
├── atlas-lab/
│   └── telemetry                        # Line Protocol (Telegraf)
│       Frequency: 10s
│       Measurements: cpu, mem, disk, system, temp
│
├── atlas-core/
│   ├── telemetry                        # Line Protocol (Telegraf + Gateway)
│   │   Frequency: 6-10s
│   │   Measurements: cpu, mem, disk, system, temp, sensors
│   └── commands                         # Commands to gateway
│       Payload: {"action": "set_interval", "value": X}
│
└── atlas-mobile/
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
├── ${ATLAS_LAB_TS_IP} (atlas-lab)
│   Services: Telegraf Agent
│   Outbound: MQTT TLS → atlas-core:8883
│
├── ${ATLAS_CORE_TS_IP} (atlas-core)
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
├── ${ATLAS_FIELD_TS_IP} (atlas-field)
│   Services: Telegraf Agent
│   Outbound: MQTT TLS → atlas-core:8883
│
└── ${ATLAS_MOBILE_TS_IP} (atlas-mobile)
    Services: Python MQTT Client
    Outbound: MQTT TLS → atlas-core:8883
```

---

## 📦 **VOLUMI DOCKER**

### **Atlas Core**
```yaml
Volumes:
  - influxdb-data: /var/lib/docker/volumes/edge-hub_influxdb-data
    Size: ~varios MB (time-series data)
    Contains: InfluxDB bucket data
  
  - influxdb-config: /var/lib/docker/volumes/edge-hub_influxdb-config
    Contains: InfluxDB configuration
  
  - grafana-data: /var/lib/docker/volumes/edge-hub_grafana-data
    Contains: Grafana dashboards, users, datasources
```

---

## 🔍 **COMANDI UTILI PER VERIFICA**

### **Atlas Lab**
```bash
# Verifica agent
sudo docker ps | grep atlas-lab
sudo docker logs atlas-agent-lab --tail=20

# Verifica certificati
ls -lh ~/mqtt-certs/
openssl x509 -in ~/mqtt-certs/atlas-lab.crt -text -noout
```

### **Atlas Core**
```bash
# Verifica stack
cd ~/atlas-infra/atlas-core/edge-hub
docker compose ps
docker compose logs -f

# Verifica Mosquitto
sudo tail -f /var/log/mosquitto/mosquitto.log
mosquitto_sub -h ${ATLAS_CORE_TS_IP} -p 1883 -t "devices/#" -v

# Verifica InfluxDB
docker exec -it edge-hub-influxdb-1 influx bucket list --org ${EDGE_INFLUX_ORG}
docker exec -it edge-hub-influxdb-1 influx query 'from(bucket:"telemetry") |> range(start:-5m) |> limit(n:10)' --org ${EDGE_INFLUX_ORG} --token ${EDGE_INFLUX_GRAFANA_TOKEN}

# Verifica certificati broker
ls -lh /etc/mosquitto/certs/
sudo openssl x509 -in /etc/mosquitto/certs/broker.crt -text -noout
```

### **ATLAS-FIELD**
```bash
# Verifica agent
docker ps | grep atlas-field
docker logs atlas-agent-field --tail=20
```

### **Atlas Mobile (Termux)**
```bash
# Verifica processo
ps aux | grep mqtt
# Verifica log (se loggato)
tail -f ~/atlas-mobile/mqtt.log
```

---

**Questa è la struttura completa e attuale. Vuoi che procediamo con l'implementazione del voice assistant o hai bisogno di altre verifiche?**
