# Aurora dashboard (OFSC)

Grafana dashboard container for OFSC.

Setup:
- Place provisioning files in `./provisioning`.
- Link the central env file into this directory:
  `ln -s /home/user/.env ./.env`
- Ensure the env contains: `OFSC_GRAFANA_ADMIN_USER`, `OFSC_GRAFANA_ADMIN_PASSWORD`.
- Start the container: `docker compose up -d`.
