#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import random
import psutil
import yaml
import logging
from datetime import datetime

# Carica configurazione
with open('/app/config/gateway.yaml', 'r') as f:
    config = yaml.safe_load(f)

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
        # Sottoscrivi topic comandi
        client.subscribe(config['mqtt']['topics']['commands'])
        logger.info(f"Sottoscritto a {config['mqtt']['topics']['commands']}")
    else:
        logger.error(f"Connessione fallita, codice: {reason_code}")

# Callback ricezione messaggi (comandi remoti)
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

# Debug Paho (utile per vedere errori callback)
def on_log(client, userdata, level, buf):
    logger.debug(f"paho: {buf}")
client.on_log = on_log

# Configura TLS se abilitato
if config['mqtt'].get('tls', {}).get('enabled', False):
    tls_config = config['mqtt']['tls']
    client.tls_set(
        ca_certs=tls_config['ca_cert'],
        certfile=tls_config['client_cert'],
        keyfile=tls_config['client_key']
    )
    logger.info("TLS abilitato per connessione MQTT")

logger.info(f"Connessione a {config['mqtt']['broker']}:{config['mqtt']['port']}")
client.connect(config['mqtt']['broker'], config['mqtt']['port'], 60)
client.loop_start()

# Attendi conferma connessione
logger.info("In attesa connessione MQTT...")
timeout = 10
while not connection_established and timeout > 0:
    time.sleep(0.5)
    timeout -= 0.5

if not connection_established:
    logger.error("Timeout connessione al broker MQTT")
    exit(1)

# Loop principale telemetria
try:
    while True:
        # Simula temperatura sensore
        temp = random.uniform(
            config['sensors']['temperature']['min'],
            config['sensors']['temperature']['max']
        )
        
        # Leggi CPU reale
        cpu = psutil.cpu_percent(interval=1)
        
        # Costruisci payload
        telemetry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'device_id': config['mqtt']['client_id'],
            'sensors': {
                'temperature': round(temp, 2),
                'cpu_usage': round(cpu, 2)
            }
        }
        
        # Pubblica su MQTT
        topic = config['mqtt']['topics']['telemetry']
        payload = json.dumps(telemetry)
        result = client.publish(topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Telemetria inviata: temp={temp:.1f}°C, cpu={cpu:.1f}%")
        else:
            logger.error(f"Errore invio telemetria: {result.rc}")
        
        time.sleep(current_interval)
        
except KeyboardInterrupt:
    logger.info("Shutdown richiesto")
    client.loop_stop()
    client.disconnect()
