#!/bin/sh
set -eu

PASSWORD_FILE="/mosquitto/config/auth/passwords"

if [ ! -f "$PASSWORD_FILE" ]; then
  mkdir -p "$(dirname "$PASSWORD_FILE")"
  mosquitto_passwd -b -c "$PASSWORD_FILE" "$MQTT_USERNAME" "$MQTT_PASSWORD"
  chmod 600 "$PASSWORD_FILE"
fi

exec mosquitto -c /mosquitto/config/mosquitto.conf
