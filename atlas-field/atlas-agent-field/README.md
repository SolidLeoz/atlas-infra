# Atlas agent (atlas-field)

This agent sends atlas-field host telemetry to the Atlas MQTT broker using TLS.

Setup:
- Place TLS certs in `./certs`: `ca.crt`, `atlas-field.crt`, `atlas-field.key`.
- Link the central env file into this directory:
  `ln -s /home/user/.env ./.env`
- Ensure the env contains: `ATLAS_FIELD_AGENT_DEVICE_ID`, `ATLAS_FIELD_AGENT_TELEGRAF_HOSTNAME`, `ATLAS_FIELD_AGENT_MQTT_URL`.
- Start the container: `docker compose up -d`.
