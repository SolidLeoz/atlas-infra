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
