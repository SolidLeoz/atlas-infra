#!/data/data/com.termux/files/usr/bin/python
"""
Atlas Mobile Watcher

Subscribes to status topics and triggers Termux notifications 
when a device goes offline or online.
"""

import os
import json
import logging
import subprocess
import paho.mqtt.client as mqtt

# --- Reuse Env Loading (Simplified for brevity but compatible) ---
def load_env():
    for path in [".env", os.path.expanduser("~/.env")]:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ.setdefault(k, v.strip("'""))
            return True
    return False

load_env()

# --- Config ---
BROKER = os.getenv("ATLAS_MOBILE_MQTT_BROKER_HOST")
PORT = int(os.getenv("ATLAS_MOBILE_MQTT_BROKER_PORT", 8883))
CLIENT_ID = f"atlas-watcher-{os.uname().nodename}"
STATUS_TOPIC = "devices/+/status"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def notify(device, status):
    title = f"Atlas Alert: {device}"
    text = f"Device is now {status.upper()}"
    color = "ff0000" if status == "offline" else "00ff00"
    
    logger.warning(f"NOTIFY: {device} is {status}")
    
    try:
        subprocess.run([
            "termux-notification",
            "--title", title,
            "--content", text,
            "--led-color", color,
            "--priority", "high",
            "--vibrate", "500,500"
        ], check=True)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to broker. Subscribing to {STATUS_TOPIC}")
        client.subscribe(STATUS_TOPIC, qos=1)
    else:
        logger.error(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        # Topic format: devices/<device_id>/status
        parts = msg.topic.split("/")
        if len(parts) >= 2:
            device = parts[1]
            status = msg.payload.decode().strip()
            notify(device, status)
    except Exception as e:
        logger.error(f"Error processing message: {e}")

# --- MQTT Setup ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

if os.getenv("ATLAS_MOBILE_MQTT_USERNAME"):
    client.username_pw_set(
        os.getenv("ATLAS_MOBILE_MQTT_USERNAME"),
        os.getenv("ATLAS_MOBILE_MQTT_PASSWORD")
    )

# TLS Setup
ca_cert = os.getenv("ATLAS_MOBILE_MQTT_CA_CERT")
cert = os.getenv("ATLAS_MOBILE_MQTT_CLIENT_CERT")
key = os.getenv("ATLAS_MOBILE_MQTT_CLIENT_KEY")

if ca_cert and os.path.exists(ca_cert):
    client.tls_set(ca_certs=ca_cert, certfile=cert, keyfile=key)
    logger.info("TLS Enabled for Watcher")

logger.info(f"Starting Watcher on {BROKER}:{PORT}...")
client.connect(BROKER, PORT, 60)
client.loop_forever()
