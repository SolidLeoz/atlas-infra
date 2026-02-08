# Aurora dashboard (OFSC) [Deprecated]

This legacy Grafana container is no longer used. The active Grafana instance
is hosted on solidserver. Keep this folder only for reference.

Setup:
- Place provisioning files in `./provisioning`.
- Link the central env file into this directory:
  `ln -s /home/user/.env ./.env`
- Ensure the env contains: `OFSC_GRAFANA_ADMIN_USER`, `OFSC_GRAFANA_ADMIN_PASSWORD`.
- Start the container: `docker compose up -d`.
