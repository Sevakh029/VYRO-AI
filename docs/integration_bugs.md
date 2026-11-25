# Week 1 integration bugs

## Verified on 2026-11-25

- **Docker runtime unavailable in the verification shell:** `docker` is not on `PATH`,
  so `docker compose up`, real Mosquitto startup, and live container health checks
  could not be executed. This is a verification blocker, not evidence of successful
  container startup.
- **Local `.env` is not present:** Compose requires `MQTT_USERNAME` and
  `MQTT_PASSWORD`. Copy `.env.example` to `.env` and replace the placeholder password
  before running the stack.
- **Mosquitto healthcheck was tightened:** The previous TCP-only probe did not verify
  that MQTT authentication works. The Compose configuration now uses `mosquitto_pub`
  with the configured credentials.

## Not verified

- Real Docker container startup and broker-to-backend connectivity
- Live HTTP health response on a running container
- Live MQTT publish/subscribe exchange through Docker networking
