# Mysa for Home Assistant

A custom Home Assistant integration for monitoring Mysa V2 thermostats and importing energy history.

> **Development status:** Initial project scaffold. Cloud authentication, live telemetry, and historical energy import are not implemented yet.

## Design goals

- Keep HomeKit as the primary thermostat control path.
- Read-only monitoring through the Mysa cloud API; no setpoint, mode, or other control commands.
- Daily energy (kWh), cumulative energy, temperature, setpoint, heating runtime, and connectivity sensors.
- Historical energy import that can fill missing dates and intervals without discarding partial days.
- HACS-compatible packaging, tests, and Home Assistant validation.

## Installation

This integration is under development and is not ready for installation.

## Configuration

Configuration and authentication flow will be documented when the read-only API client is implemented.

## Privacy and security

Credentials will be handled through Home Assistant's config-entry storage. Never include passwords, access tokens, or full device identifiers in diagnostic reports or issue submissions.

## Development

The integration targets current Home Assistant Core and follows the standard custom integration layout under `custom_components/mysa`.
