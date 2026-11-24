#!/bin/sh
set -eu

PASSWORD_FILE="/mosquitto/data/passwords"

if [ ! -f "$PASSWORD_FILE" ]; then
  mkdir -p "$(dirname "$PASSWORD_FILE")"
  printf '%s\n%s\n' "$MQTT_PASSWORD" "$MQTT_PASSWORD" |
    mosquitto_passwd -c "$PASSWORD_FILE" "$MQTT_USERNAME"
  chmod 600 "$PASSWORD_FILE"
  chown mosquitto:mosquitto "$PASSWORD_FILE"
fi

exec mosquitto -c /mosquitto/config/mosquitto.conf
