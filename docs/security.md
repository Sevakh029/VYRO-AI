# Security and privacy

## Transport

The Mosquitto listener is password protected. Clients authenticate with
`MQTT_USERNAME` and `MQTT_PASSWORD`; anonymous access is disabled.

The Docker Compose development setup generates its configured credential file
inside the broker volume and assigns it to the Mosquitto runtime user. Never
commit real credentials or password files.

## Validation

The backend rejects malformed JSON, unsupported topics, oversized MQTT payloads,
impossible vehicle states, and excessive message rates. Payloads are preserved
in SQLite for diagnostics before Pydantic validation.

## Privacy

Vehicle IDs may be run-pseudonymized with a SHA-256 HMAC-style run-specific
digest. Logs are bounded by `VYRO_LOG_RETENTION_LIMIT` and personal fields such
as names, email addresses, phone numbers, and exact GPS fields are rejected by
the privacy schema checker.
