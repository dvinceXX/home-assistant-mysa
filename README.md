# Mysa for Home Assistant

A custom Home Assistant integration for monitoring Mysa thermostats through the Mysa cloud API.

> **Development status:** Early development. Account authentication and live monitoring sensors are implemented. Historical energy import is still under development; do not install this version expecting Energy dashboard history.

## Current features

- Mysa account sign-in and account/device discovery.
- Secure refresh-token handling with automatic re-authentication using the stored account credentials when needed.
- Read-only room temperature, heat setpoint, and connectivity entities.
- Five-minute polling through Home Assistant's shared HTTP session.
- HACS-compatible custom integration structure and initial automated tests.

## Design goals

- Keep HomeKit as the primary thermostat control path.
- This integration is monitoring-only. It does not send setpoint, mode, schedule, or other thermostat control commands.
- Add verified daily energy (kWh), cumulative energy, and historical energy import.
- Import missing history without treating a partially imported day as complete.

## Installation

This integration is under development and is not yet recommended for production use.

## Configuration

Add the **Mysa** integration in Home Assistant and enter your Mysa account email and password. Authentication is validated during setup. Credentials and the Cognito refresh token are stored in the Home Assistant config entry; they are never written to the integration logs.

Some Mysa accounts may require an additional authentication challenge (for example, MFA or a new-password challenge). Those flows are not supported yet.

## Privacy and security

The cloud API is unofficial and undocumented. Use it at your own risk. Never include passwords, access tokens, or full device identifiers in diagnostic reports or issue submissions.

## Development

The integration lives under `custom_components/mysa`. Tests run with pytest and the Home Assistant custom-component test package.
