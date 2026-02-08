#!/usr/bin/env python3
import os
import paho.mqtt.client as mqtt
import json
import time
import random
import psutil
import yaml
import logging
from datetime import datetime

def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)

def _resolve_env(value, env_key, cast=None):
    env_val = os.getenv(env_key)
    if env_val is not None:
        value = env_val
    elif isinstance(value, str) and value.strip() == f"${{{env_key}}}":
        raise RuntimeError(f"Missing required env var: {env_key}")
    if cast:
        return cast(value)
    return value

# Carica configurazione
with open('/app/config/gateway.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Override/resolve config via env (no hardcoded addresses or secrets)
config['mqtt']['broker'] = _resolve_env(
    config['mqtt']['broker'],
    'GATEWAY_MQTT_BROKER_HOST'
)
config['mqtt']['port'] = _resolve_env(
    config['mqtt']['port'],
    'GATEWAY_MQTT_BROKER_PORT',
    cast=int
)
config['mqtt']['client_id'] = _resolve_env(
    config['mqtt']['client_id'],
    'GATEWAY_MQTT_CLIENT_ID'
)
config['mqtt']['topics']['telemetry'] = _resolve_env(
    config['mqtt']['topics']['telemetry'],
    'GATEWAY_MQTT_TELEMETRY_TOPIC'
)
config['mqtt']['topics']['commands'] = _resolve_env(
    config['mqtt']['topics']['commands'],
    'GATEWAY_MQTT_COMMANDS_TOPIC'
)
config['mqtt']['tls']['enabled'] = _resolve_env(
    config['mqtt']['tls'].get('enabled', False),
    'GATEWAY_MQTT_TLS_ENABLED',
    cast=_to_bool
)
config['logging']['level'] = _resolve_env(
    config['logging']['level'],
    'GATEWAY_LOG_LEVEL'
)
config['logging']['file'] = _resolve_env(
    config['logging']['file'],
    'GATEWAY_LOG_FILE'
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config['logging']['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Variabili globali
current_interval = config['sensors']['temperature']['interval']
connection_established = False

# Callback connessione MQTT
def on_connect(client, userdata, flags, reason_code, properties=None):
    global connection_established
    if getattr(reason_code, "value", reason_code) == 0:
        logger.info(f"Connesso al broker MQTT")
        connection_established = True
        client.subscribe(config['mqtt']['topics']['commands'])
        logger.info(f"Sottoscritto a {config['mqtt']['topics']['commands']}")
    else:
        logger.error(f"Connessione fallita, codice: {reason_code}")

# Callback ricezione messaggi
def on_message(client, userdata, msg):
    global current_interval
    logger.info(f"Comando ricevuto su {msg.topic}: {msg.payload.decode()}")
    try:
        command = json.loads(msg.payload.decode())
        if command.get('action') == 'set_interval':
            new_interval = command['value']
            current_interval = new_interval
            logger.info(f"✅ Intervallo telemetria cambiato a {new_interval}s")
        else:
            logger.warning(f"Azione sconosciuta: {command.get('action')}")
    except Exception as e:
        logger.error(f"Errore processing comando: {e}")

# Setup client MQTT
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=config['mqtt']['client_id']
)
client.on_connect = on_connect
client.on_message = on_message

# Configura TLS se abilitato
if config['mqtt'].get('tls', {}).get('enabled', False):
    tls_config = config['mqtt']['tls']
    client.tls_set(
        ca_certs=tls_config['ca_cert'],
        certfile=tls_config.get('certfile'),
        keyfile=tls_config.get('keyfile')
    )
    logger.info("TLS configurato")

# Connetti al broker
logger.info(f"Connessione a {config['mqtt']['broker']}:{config['mqtt']['port']}")
client.connect(
    config['mqtt']['broker'],
    config['mqtt']['port'],
    60
)
client.loop_start()

# Attendi connessione
timeout = 10
for _ in range(timeout):
    if connection_established:
        break
    time.sleep(1)
else:
    logger.error("Timeout connessione al broker")
    exit(1)

# Loop principale telemetria
try:
    while True:
        # Leggi sensori con fallback
        try:
            temps = psutil.sensors_temperatures()
            if temps and 'coretemp' in temps and len(temps['coretemp']) > 0:
                temp = temps['coretemp'][0].current
            else:
                temp = 20.0 + random.uniform(-2, 2)
        except:
            temp = 20.0 + random.uniform(-2, 2)
        
        cpu = psutil.cpu_percent(interval=1)
        
        # Costruisci payload in Line Protocol
        timestamp_ns = int(time.time() * 1e9)
        device_id = config['mqtt']['client_id']
        
        lines = [
            f"sensors,device={device_id},sensor=temperature value={temp:.2f} {timestamp_ns}",
            f"sensors,device={device_id},sensor=cpu_usage value={cpu:.2f} {timestamp_ns}"
        ]
        payload = "\n".join(lines)
        
        # Pubblica su MQTT
        topic = config['mqtt']['topics']['telemetry']
        result = client.publish(topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Telemetria inviata: temp={temp:.1f}°C, cpu={cpu:.1f}%")
        else:
            logger.error(f"Errore invio telemetria: {result.rc}")
        
        time.sleep(current_interval)
        
except KeyboardInterrupt:
    logger.info("Shutdown richiesto")
finally:
    client.loop_stop()
    client.disconnect()
    logger.info("Gateway disconnesso")
