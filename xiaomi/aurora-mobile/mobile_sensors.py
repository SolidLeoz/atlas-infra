#!/data/data/com.termux/files/usr/bin/python
"""
Aurora Mobile Sensors (Termux)

OBIETTIVO:
- Client MQTT su Termux con TLS + QoS=1
- Evitare disconnessioni/reconnect loop causate da CLIENT_ID duplicati:
  -> client-id dinamico (unico) + lockfile singleton
- Pubblica telemetria e batteria
- Riceve comandi su topic configurato ed esegue termux-* async
"""

import json
import time
import yaml
import logging
import subprocess
import threading
import socket
import uuid
import os
import sys
import fcntl
import shutil

import paho.mqtt.client as mqtt


# ----------------------------
# Env loader (.env)
# ----------------------------
def load_env_file():
    candidates = []
    env_path = os.environ.get("AURORA_ENV_FILE")
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.expanduser("~"), ".env"),
        ]
    )
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                os.environ.setdefault(key, value)
        return path
    return None


def expand_env(obj):
    if isinstance(obj, dict):
        return {k: expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env(v) for v in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def is_unresolved(value):
    return isinstance(value, str) and ("${" in value or value.startswith("$"))


def env_value(name):
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def coerce_int(value, label):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer") from exc


def resolve_topic(value, fallback):
    if not value or is_unresolved(value):
        return fallback
    return value


def _escape_measurement(value):
    return str(value).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,")


def _escape_tag(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _escape_field_key(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _format_fields(fields):
    parts = []
    for key, value in fields.items():
        if value is None:
            continue
        key = _escape_field_key(key)
        if isinstance(value, bool):
            parts.append(f"{key}={str(value).lower()}")
        elif isinstance(value, int):
            parts.append(f"{key}={value}i")
        elif isinstance(value, float):
            parts.append(f"{key}={value}")
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{key}="{escaped}"')
    return ",".join(parts)


def _format_line_protocol(measurement, tags, fields, timestamp_ns):
    measurement = _escape_measurement(measurement)
    tags_part = ",".join(
        f"{_escape_tag(k)}={_escape_tag(v)}" for k, v in (tags or {}).items() if v is not None
    )
    fields_part = _format_fields(fields or {})
    if not fields_part:
        return None
    if tags_part:
        measurement = f"{measurement},{tags_part}"
    return f"{measurement} {fields_part} {timestamp_ns}"


# ----------------------------
# Carica configurazione
# ----------------------------
env_path = load_env_file()
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

config = expand_env(config)

mqtt_cfg = config.setdefault("mqtt", {})
topics_cfg = mqtt_cfg.setdefault("topics", {})
sensors_topics_cfg = topics_cfg.setdefault("sensors", {})
sensors_cfg = config.setdefault("sensors", {})
logging_cfg = config.setdefault("logging", {})

broker_env = env_value("XIAOMI_MQTT_BROKER_HOST")
port_env = env_value("XIAOMI_MQTT_BROKER_PORT")
client_id_env = env_value("XIAOMI_MQTT_CLIENT_ID")
username_env = env_value("XIAOMI_MQTT_USERNAME")
password_env = env_value("XIAOMI_MQTT_PASSWORD")
telemetry_topic_env = env_value("XIAOMI_MQTT_TELEMETRY_TOPIC")
commands_topic_env = env_value("XIAOMI_MQTT_COMMANDS_TOPIC")
battery_topic_env = env_value("XIAOMI_MQTT_SENSORS_BATTERY_TOPIC")
location_topic_env = env_value("XIAOMI_MQTT_SENSORS_LOCATION_TOPIC")
sensor_topic_env = env_value("XIAOMI_MQTT_SENSORS_SENSOR_TOPIC")
interval_env = env_value("XIAOMI_SENSORS_INTERVAL")

if broker_env:
    mqtt_cfg["broker"] = broker_env
if port_env:
    mqtt_cfg["port"] = port_env
if client_id_env:
    mqtt_cfg["client_id"] = client_id_env
if username_env:
    mqtt_cfg["username"] = username_env
if password_env:
    mqtt_cfg["password"] = password_env
if telemetry_topic_env:
    topics_cfg["telemetry"] = telemetry_topic_env
if commands_topic_env:
    topics_cfg["commands"] = commands_topic_env
if battery_topic_env:
    sensors_topics_cfg["battery"] = battery_topic_env
if location_topic_env:
    sensors_topics_cfg["location"] = location_topic_env
if sensor_topic_env:
    sensors_topics_cfg["sensor"] = sensor_topic_env
if interval_env:
    sensors_cfg["interval"] = interval_env

mqtt_cfg["port"] = coerce_int(mqtt_cfg.get("port"), "mqtt.port")
sensors_cfg["interval"] = coerce_int(sensors_cfg.get("interval") or 10, "sensors.interval") or 10

if is_unresolved(mqtt_cfg.get("broker")):
    mqtt_cfg["broker"] = None
if is_unresolved(mqtt_cfg.get("client_id")):
    mqtt_cfg["client_id"] = None
if is_unresolved(mqtt_cfg.get("username")):
    mqtt_cfg["username"] = None
if is_unresolved(mqtt_cfg.get("password")):
    mqtt_cfg["password"] = None

if mqtt_cfg.get("broker") is None or mqtt_cfg.get("port") is None or mqtt_cfg.get("client_id") is None:
    raise SystemExit("Missing required MQTT settings. Check XIAOMI_* values in .env.")

device_id = mqtt_cfg["client_id"]
topics_cfg["telemetry"] = resolve_topic(
    topics_cfg.get("telemetry"),
    f"devices/{device_id}/telemetry",
)
topics_cfg["commands"] = resolve_topic(
    topics_cfg.get("commands"),
    "devices/xiaomi/commands",
)
sensors_topics_cfg["battery"] = resolve_topic(
    sensors_topics_cfg.get("battery"),
    f"devices/{device_id}/sensors/battery",
)
sensors_topics_cfg["location"] = resolve_topic(
    sensors_topics_cfg.get("location"),
    f"devices/{device_id}/sensors/location",
)
sensors_topics_cfg["sensor"] = resolve_topic(
    sensors_topics_cfg.get("sensor"),
    f"devices/{device_id}/sensors/sensor",
)


# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(
    level=getattr(logging, logging_cfg.get("level", "INFO")),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if env_path:
    logger.info(f"Env caricato da: {env_path}")


# ----------------------------
# Singleton lock (ANTI DOPPIO AVVIO)
# ----------------------------
LOCK_DIR = os.path.join(os.path.expanduser("~"), ".aurora-lock")
LOCK_PATH = os.path.join(LOCK_DIR, "mobile_sensors.lock")

try:
    os.makedirs(LOCK_DIR, exist_ok=True)
    _lockfile = open(LOCK_PATH, "w")
    fcntl.flock(_lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    logger.error("Istanza gia in esecuzione (lock presente). Esco.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Impossibile acquisire lock: {e}")
    sys.exit(1)


# ----------------------------
# Identita dispositivi
# ----------------------------
DEVICE_ID = device_id
MQTT_CLIENT_ID = f"{DEVICE_ID}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
DISK_PATH = os.path.expanduser(env_value("XIAOMI_DISK_PATH") or "~")

logger.info(f"DEVICE_ID (payload): {DEVICE_ID}")
logger.info(f"MQTT_CLIENT_ID (connessione): {MQTT_CLIENT_ID}")
logger.info(f"DISK_PATH: {DISK_PATH}")


# ----------------------------
# Sensori Termux (con retry)
# ----------------------------
def get_battery_status(retries: int = 2):
    """Legge stato batteria via termux-battery-status con retry"""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout batteria (tentativo {attempt+1}/{retries})")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Errore batteria: {e}")
            time.sleep(0.5)
    return None


_prev_cpu_total = None
_prev_cpu_idle = None


def _read_first_line(path):
    try:
        with open(path, "r") as f:
            return f.readline().strip()
    except Exception:
        return None


def get_cpu_usage_active():
    global _prev_cpu_total, _prev_cpu_idle
    line = _read_first_line("/proc/stat")
    if not line or not line.startswith("cpu "):
        return get_cpu_usage_from_top()
    parts = line.split()
    try:
        values = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    if _prev_cpu_total is None:
        _prev_cpu_total = total
        _prev_cpu_idle = idle
        return None
    delta_total = total - _prev_cpu_total
    delta_idle = idle - _prev_cpu_idle
    _prev_cpu_total = total
    _prev_cpu_idle = idle
    if delta_total <= 0:
        return get_cpu_usage_from_top()
    usage = 100.0 * (delta_total - delta_idle) / delta_total
    if usage < 0:
        return 0.0
    if usage > 100:
        return 100.0
    return usage


def get_cpu_usage_from_top():
    try:
        result = subprocess.run(
            ["top", "-b", "-n", "1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if "%cpu" not in line or "%idle" not in line:
                continue
            total_pct = None
            idle_pct = None
            for token in line.split():
                if token.endswith("%cpu"):
                    total_pct = float(token.replace("%cpu", ""))
                elif token.endswith("%idle"):
                    idle_pct = float(token.replace("%idle", ""))
            if total_pct is None or idle_pct is None or total_pct <= 0:
                return None
            usage = (total_pct - idle_pct) / total_pct * 100.0
            if usage < 0:
                return 0.0
            if usage > 100:
                return 100.0
            return usage
    except Exception:
        return None


def get_mem_used_percent():
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip().split()[0]
                meminfo[key] = int(value)
        mem_total = meminfo.get("MemTotal")
        mem_available = meminfo.get("MemAvailable")
        if mem_total is None:
            return None
        if mem_available is None:
            mem_free = meminfo.get("MemFree", 0)
            buffers = meminfo.get("Buffers", 0)
            cached = meminfo.get("Cached", 0)
            mem_available = mem_free + buffers + cached
        used = mem_total - mem_available
        if mem_total <= 0:
            return None
        return (used / mem_total) * 100.0
    except Exception:
        return None


def get_disk_used_percent(path):
    try:
        usage = shutil.disk_usage(path)
        if usage.total <= 0:
            return None
        return (usage.used / usage.total) * 100.0
    except Exception:
        return None


def _parse_uptime_line(line):
    if not line:
        return None, None
    if "load average" not in line:
        return None, None
    before, _, after = line.partition("load average:")
    load1 = None
    try:
        load1 = float(after.strip().split(",")[0])
    except (ValueError, IndexError):
        load1 = None
    uptime_seconds = None
    up_idx = before.find(" up ")
    if up_idx != -1:
        uptime_str = before[up_idx + 4 :].strip().rstrip(",")
        days = 0
        hours = 0
        minutes = 0
        for part in [p.strip() for p in uptime_str.split(",") if p.strip()]:
            if "day" in part:
                try:
                    days += int(part.split()[0])
                except (ValueError, IndexError):
                    pass
            elif ":" in part:
                try:
                    hour_str, min_str = part.split(":", 1)
                    hours += int(hour_str)
                    minutes += int(min_str)
                except (ValueError, IndexError):
                    pass
            elif "min" in part:
                try:
                    minutes += int(part.split()[0])
                except (ValueError, IndexError):
                    pass
            elif "hr" in part:
                try:
                    hours += int(part.split()[0])
                except (ValueError, IndexError):
                    pass
        uptime_seconds = (days * 86400) + (hours * 3600) + (minutes * 60)
    return uptime_seconds, load1


def get_uptime_and_load():
    uptime_seconds = None
    load1 = None
    line = _read_first_line("/proc/uptime")
    if line:
        try:
            uptime_seconds = int(float(line.split()[0]))
        except (ValueError, IndexError):
            uptime_seconds = None
    line = _read_first_line("/proc/loadavg")
    if line:
        try:
            load1 = float(line.split()[0])
        except (ValueError, IndexError):
            load1 = None
    if uptime_seconds is not None or load1 is not None:
        return uptime_seconds, load1
    try:
        result = subprocess.run(
            ["uptime"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None, None
        return _parse_uptime_line(result.stdout.strip())
    except Exception:
        return None, None


# ----------------------------
# Comandi (async)
# ----------------------------
def execute_command_async(command_data: dict):
    """Esegue comando in thread separato per non bloccare loop MQTT"""
    action = command_data.get("action")
    try:
        if action == "vibrate":
            result = subprocess.run(
                ["termux-vibrate", "-d", "500"],
                timeout=2,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info("Vibrazione eseguita")
            else:
                logger.warning(
                    f"Vibrazione fallita: rc={result.returncode} err={result.stderr.strip()}"
                )
        elif action == "notification":
            title = command_data.get("title", "Aurora")
            text = command_data.get("text", "Notifica")
            result = subprocess.run(
                ["termux-notification", "--title", title, "--content", text],
                timeout=3,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info(f"Notifica: {title}")
            else:
                logger.warning(
                    f"Notifica fallita: rc={result.returncode} err={result.stderr.strip()}"
                )
        else:
            logger.warning(f"Azione non supportata: {action}")
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout esecuzione comando: {action}")
    except Exception as e:
        logger.error(f"Errore comando ({action}): {e}")


# ----------------------------
# Callback MQTT
# ----------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connesso al broker MQTT")
        client.subscribe(topics_cfg["commands"], qos=1)
        logger.info(f"Sottoscritto a {topics_cfg['commands']} (QoS 1)")
    else:
        logger.error(f"Connessione fallita: rc={rc}")


def on_disconnect(client, userdata, rc, properties=None, reason_code=None):
    if rc != 0:
        logger.warning(f"Disconnesso in modo inatteso (rc={rc}). Il loop tenterà reconnect.")
    else:
        logger.info("Disconnesso dal broker (rc=0)")


def on_message(client, userdata, msg):
    """Gestione comandi con threading"""
    payload = msg.payload.decode(errors="replace")
    logger.info(f"Comando: {payload}")
    try:
        command = json.loads(payload)
        thread = threading.Thread(
            target=execute_command_async, args=(command,), daemon=True
        )
        thread.start()
    except Exception as e:
        logger.error(f"Errore parsing comando: {e}")


# ----------------------------
# Setup client MQTT (TLS + QoS)
# ----------------------------
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=MQTT_CLIENT_ID,
    clean_session=True,
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

if mqtt_cfg.get("username"):
    client.username_pw_set(mqtt_cfg["username"], mqtt_cfg.get("password"))

if mqtt_cfg.get("tls", {}).get("enabled"):
    tls_cfg = mqtt_cfg["tls"]
    ca_cert = tls_cfg.get("ca_cert")
    client_cert = tls_cfg.get("client_cert")
    client_key = tls_cfg.get("client_key")
    if is_unresolved(ca_cert) or is_unresolved(client_cert) or is_unresolved(client_key):
        raise SystemExit("Missing TLS cert paths. Check config.yaml or .env.")
    client.tls_set(
        ca_certs=ca_cert,
        certfile=client_cert,
        keyfile=client_key,
    )
    client.tls_insecure_set(False)
    logger.info("TLS abilitato")

BROKER = mqtt_cfg["broker"]
PORT = mqtt_cfg["port"]

logger.info(f"Connessione a {BROKER}:{PORT}")
client.connect(BROKER, PORT, 60)
client.loop_start()


# ----------------------------
# Loop principale telemetria
# ----------------------------
try:
    iteration = 0
    while True:
        iteration += 1
        timestamp_ns = int(time.time() * 1_000_000_000)
        battery = get_battery_status()
        percentage = None
        temperature = None
        status = None

        if battery:
            percentage = battery.get("percentage")
            temperature = battery.get("temperature")
            status = battery.get("status") or "unknown"

            battery_fields = {}
            if percentage is not None:
                battery_fields["percentage"] = float(percentage)
            if temperature is not None:
                battery_fields["temperature"] = float(temperature)

            battery_line = _format_line_protocol(
                "mobile_battery",
                {"status": status},
                battery_fields,
                timestamp_ns,
            )
            if battery_line:
                client.publish(
                    sensors_topics_cfg["battery"],
                    battery_line,
                    qos=1,
                )

            logger.info(
                f"Telemetria #{iteration} - Batteria: {battery.get('percentage')}%"
            )
        else:
            logger.warning(f"Telemetria #{iteration} - Batteria: N/A (timeout)")

        lines = []
        telemetry_fields = {"iteration": int(iteration)}
        if percentage is not None:
            telemetry_fields["battery_percent"] = float(percentage)
        if temperature is not None:
            telemetry_fields["battery_temp"] = float(temperature)

        telemetry_tags = {"status": status} if status else None
        telemetry_line = _format_line_protocol(
            "mobile_telemetry",
            telemetry_tags,
            telemetry_fields,
            timestamp_ns,
        )
        if telemetry_line:
            lines.append(telemetry_line)

        cpu_usage = get_cpu_usage_active()
        if cpu_usage is not None:
            cpu_line = _format_line_protocol(
                "cpu",
                {"cpu": "cpu-total"},
                {"usage_active": float(cpu_usage)},
                timestamp_ns,
            )
            if cpu_line:
                lines.append(cpu_line)

        mem_used = get_mem_used_percent()
        if mem_used is not None:
            mem_line = _format_line_protocol(
                "mem",
                None,
                {"used_percent": float(mem_used)},
                timestamp_ns,
            )
            if mem_line:
                lines.append(mem_line)

        disk_used = get_disk_used_percent(DISK_PATH)
        if disk_used is not None:
            disk_line = _format_line_protocol(
                "disk",
                {"path": DISK_PATH},
                {"used_percent": float(disk_used)},
                timestamp_ns,
            )
            if disk_line:
                lines.append(disk_line)

        system_fields = {}
        uptime_seconds, load1 = get_uptime_and_load()
        if uptime_seconds is not None:
            system_fields["uptime"] = int(uptime_seconds)
        if load1 is not None:
            system_fields["load1"] = float(load1)
        if system_fields:
            system_line = _format_line_protocol(
                "system",
                None,
                system_fields,
                timestamp_ns,
            )
            if system_line:
                lines.append(system_line)

        if temperature is not None:
            temp_line = _format_line_protocol(
                "temp",
                {"sensor": "battery"},
                {"temp": float(temperature)},
                timestamp_ns,
            )
            if temp_line:
                lines.append(temp_line)

        if lines:
            payload = "\n".join(lines)
            client.publish(
                topics_cfg["telemetry"],
                payload,
                qos=1,
            )

        time.sleep(sensors_cfg["interval"])

except KeyboardInterrupt:
    logger.info("Shutdown (CTRL+C)")
finally:
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass
