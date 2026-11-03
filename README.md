# Mysa for Home Assistant

A custom Home Assistant integration for monitoring Mysa thermostats through the Mysa cloud API.

> **Development status:** Early development. Read-only monitoring and expanded energy history are implemented. The cloud API is unofficial and has only been validated against selected hardware.

## Features

- Mysa account sign-in and account/device discovery.
- Room temperature, heat setpoint, and connectivity entities.
- Daily energy (kWh) and cumulative energy sensors for each thermostat.
- Historical energy import into Home Assistant long-term statistics, including hourly buckets for the Energy dashboard.
- Persistent local history with a 365-day initial backfill and a rolling 30-day refresh to repair partial days and recover after downtime.
- Five-minute live-state polling and 12-hour energy-history polling.

## HomeKit and control

Keep HomeKit as the primary thermostat control path. This integration is monitoring-only: it does not send setpoint, mode, schedule, or other thermostat control commands.

## Installation

This integration is under development and is not yet recommended for production use.

## Configuration

Add the **Mysa** integration in Home Assistant and enter your Mysa account email and password. Authentication is validated during setup. Credentials and the Cognito refresh token are stored in the Home Assistant config entry and are not written to integration logs.

## Energy data notes

Energy uses the expanded Mysa usage API's `k` metric. It does not estimate energy from heating runtime or assumed heater wattage. Mysa's API is undocumented, and energy availability may differ by thermostat model. If a device does not return `k`, the integration leaves its energy sensors unavailable rather than inventing a value.

The integration stores the daily history locally and imports external hourly statistics with stable statistic IDs. Re-importing the same time periods updates existing statistics instead of creating duplicates.

## Privacy and security

The cloud API is unofficial and undocumented. Use it at your own risk. Never include passwords, access tokens, or full device identifiers in diagnostic reports or issue submissions.

## Development

The integration lives under `custom_components/mysa`. Tests run with pytest and the Home Assistant custom-component test package.
