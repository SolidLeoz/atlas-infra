# Aurora mobile (Xiaomi telemetry)

Termux-based MQTT telemetry client for Xiaomi.

Setup:
- Copy this folder to `~/aurora-mobile` on the phone.
- Place TLS certs in `~/aurora-mobile/certs`: `ca.crt`, `mobile.crt`, `mobile.key`.
- Create a central env at `~/.env` and link it into the folder:
  `ln -s ~/.env ~/aurora-mobile/.env`
- Ensure the env contains the `XIAOMI_*` variables from the root `.env.example`.
- Install Termux boot scripts from `termux-boot/` into `~/.termux/boot/`.
- Start manually: `python mobile_sensors.py`.

Telemetry format:
- Publishes Influx line protocol.
- Topics/measurements:
  - `devices/<device>/sensors/battery` -> `mobile_battery` (percentage, temperature, status tag)
  - `devices/<device>/telemetry` -> `mobile_telemetry` (iteration, battery_percent, battery_temp, status tag)
