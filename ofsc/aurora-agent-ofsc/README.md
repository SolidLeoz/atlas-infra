# Aurora agent (OFSC)

This agent sends OFSC host telemetry to the Aurora MQTT broker using TLS.

Setup:
- Place TLS certs in `./certs`: `ca.crt`, `ofsc.crt`, `ofsc.key`.
- Link the central env file into this directory:
  `ln -s /home/user/.env ./.env`
- Ensure the env contains: `OFSC_AGENT_DEVICE_ID`, `OFSC_AGENT_TELEGRAF_HOSTNAME`, `OFSC_AGENT_MQTT_URL`.
- Start the container: `docker compose up -d`.
