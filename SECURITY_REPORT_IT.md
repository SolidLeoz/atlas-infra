# Atlas Research Infrastructure – Report di Sicurezza e Best Practices

**Data (UTC):** 2026-02-10T20:11:42Z  
**Scope:** analisi completa del repository + stato runtime attuale  
**Autore:** Codex (assistente)

---

## 1) Executive Summary
Atlas Infra è uno stack di telemetria TLS‑first su Tailscale basato su MQTT, Telegraf, InfluxDB e Grafana.  
La struttura è solida: separazione dei segreti, mTLS per MQTT, token Influx least‑privilege e provisioning
automatizzato. I rischi principali sono legati all’hardening operativo (host networking, TLS verify opzionale,
broker non‑TLS locale) e alla presenza di container non collegati al progetto sul nodo core.

---

## 2) Architettura (statico)
**Ruoli:**
- **atlas-core:** Mosquitto (systemd), InfluxDB, Grafana, Telegraf collector + Telegraf agent.
- **atlas-lab / atlas-field:** agent Telegraf che pubblicano metriche su MQTT TLS.
- **atlas-mobile:** client Termux Python che pubblica telemetria e batteria via MQTT TLS.

**Data flow:**
`Device → MQTT TLS → Telegraf (collector) → InfluxDB → Grafana`

---

## 3) Perché ci sono i container Docker
- **Isolamento e portabilità** tra host differenti.
- **Versioning e riproducibilità** (immagini versionate: Influx/Grafana/Telegraf).
- **Operatività**: restart automatico, deploy uniforme con `docker compose`.

---

## 4) Best practices rispettate
### Sicurezza
- **mTLS (X.509)** per tutte le connessioni MQTT esterne.
- **Least‑privilege tokens**: token separati per Grafana (read) e Telegraf (write).
- **Segreti fuori da Git**: `.env` e cert ignorati.
- **Grafana** con signup disabilitato.
- **ACL Mosquitto** supportate (opzionali).

### Programmazione / Operatività
- **Config centralizzata** via `.env` e template con `envsubst`.
- **Config runtime generate** (non versionate) per ridurre leakage.
- **Client mobile robusto**: lockfile per singleton, client ID univoco, logging e fallback.

---

## 5) Gap / Rischi residui (priorità)
**Alta**
- **Host networking** su più container (telegraf/agent): riduce isolamento.  

**Media**
- **`tlsSkipVerify` configurabile** per datasource Influx: se abilitato, riduce la sicurezza TLS.
- **MQTT non‑TLS locale con `allow_anonymous`**: sicuro solo se bindato a `127.0.0.1`.
- **Container non‑relativi al progetto** attivi su atlas-core (superficie d’attacco laterale).

**Bassa**
- Mancano **healthcheck** espliciti e **limiti risorse** nei compose.

---

## 6) Raccomandazioni operative (pragmatiche)
1. **Ridurre host networking** ove possibile (bridge + mount /proc,/sys read‑only).
2. **Forzare TLS verify** per Influx quando usi HTTPS (CA valida).
3. **Bloccare listener non‑TLS** se non necessario (o mantenere bind 127.0.0.1).
4. **Aggiungere healthcheck/limits** per container core.
5. **Separare host “lab/security”** dagli host di produzione del core, o isolare via firewall/ACL.

---

## 7) Stato runtime attuale (evidenze)
**Core (solidserver)**
- `docker` **enabled/active**
- `mosquitto` **enabled/active**
- Container core attivi:
  - `edge-hub-influxdb-1`, `edge-hub-telegraf-1`, `edge-hub-grafana-*`, `atlas-agent-core`
  - presenti anche container non‑relativi al progetto: `juice-shop`, `kali`, `webgoat`, `dvwa`
- Grafana health: **ok** (versione 10.2.3)
- Influx (ultimi 5 min): **atlas-core, atlas-lab, atlas-field, atlas-mobile**
- Misure `sensors` (mock): **assenti** negli ultimi 5 minuti

**Field (ofsc)**
- `docker` **enabled/active**
- `atlas-agent-field` **Up**

**Lab (workstation)**
- `snap.docker.dockerd` **active/enabled**
- `atlas-agent-lab` **running** (telemetria OK)

**Mobile (xiaomi)**
- `mobile_sensors.py` **in esecuzione**
- Log: telemetria batteria in invio

---

## 8) Checklist di verifica operativa
**Core**
- `systemctl is-active docker && systemctl is-active mosquitto`
- `docker ps | grep edge-hub`
- `curl http://127.0.0.1:3001/api/health`
- Query Influx per device attivi

**Lab / Field**
- `systemctl is-active docker` (o `snap.docker.dockerd` su lab)
- `docker ps | grep atlas-agent-*`

**Mobile**
- `pgrep -af mobile_sensors.py`
- `tail -n 20 ~/atlas-mobile/nohup.out`

---

## 9) Conclusione
L’infrastruttura è correttamente progettata e sicura per un contesto accademico/lab, con scelte tecniche coerenti
con le best practices moderne. I punti da migliorare sono operativi (hardening) più che architetturali.

