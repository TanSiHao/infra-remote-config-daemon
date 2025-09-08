# LaunchDarkly → .env Sync Daemon (Python)

A Python daemon that listens to LaunchDarkly via SSE and keeps a local `.env` file in sync with evaluated feature flag values. On any flag change, it backs up the current `.env` with a timestamp and writes the latest values.

## Requirements

- Python 3.9+
- Install deps: `pip install -r requirements.txt`

## Configuration (environment variables)

- `LD_SDK_KEY` (required): LaunchDarkly server-side SDK key
- `FLAGS` (optional): Comma-separated flag keys; default: `SAMPLE_API_URL,SAMPLE_SERVICE_URL,SAMPLE_APP_URL`
- `ENV_FILE_PATH` (optional): Path to `.env`; default: `.env`
- `BACKUP_ENABLED` (optional): `true`/`false`; default: `true`
- `LOG_LEVEL` (optional): `DEBUG|INFO|WARNING|ERROR|CRITICAL`; default: `INFO`
- `DEBOUNCE_MS` (optional): Debounce milliseconds for rapid updates; default: `400`
- `LD_CONTEXT_KEY` (optional): Evaluation context key; default: `sample-daemon`
- `LD_CONTEXT_NAME` (optional): Evaluation context name; default: `Daemon`

## Run

```bash
export LD_SDK_KEY=YOUR_SERVER_SDK_KEY
python ld_env_sync_daemon.py
```

The daemon will:
- Initialize LaunchDarkly SDK and await initial data
- Perform initial evaluation of configured flags and write to `.env`
- Listen for flag changes and update `.env` after creating a timestamped backup

## Provision flags (Terraform)

This repo includes Terraform to create the three flags the daemon expects, with string variations and mock URLs:

- `SAMPLE_API_URL`
  - API v2 → `https://api-v2.example.com`
  - API v1 → `https://api-v1.example.com`
  - fallback API → `https://api-default.example.com`
- `SAMPLE_SERVICE_URL`
  - SAMPLE_APP_URL v2 → `https://app-api-v2.example.com`
  - SAMPLE_APP_URL v1 → `https://app-api-v1.example.com`
  - SAMPLE_APP_URL Base → `https://app-api.example.com`
- `SAMPLE_APP_URL`
  - SAMPLE_APP_URL v2 → `https://app-api-v2.example.com`
  - SAMPLE_APP_URL v1 → `https://app-api-v1.example.com`
  - SAMPLE_APP_URL Base → `https://app-api.example.com`

Apply:

```bash
cd terraform
terraform init
terraform apply \
  -var launchdarkly_access_token=YOUR_LD_API_TOKEN \
  -var project_key=YOUR_PROJECT_KEY \
  -var environment_key=YOUR_ENV_KEY
```

## Notes

- Env var names match flag keys 1:1. Values are written as strings.
- File permissions for `.env` are set to owner read/write (0600) where supported.
- If a flag is missing or wrong type, an empty string is written and a warning is logged.

### Troubleshooting

- Empty values in `.env` usually mean the flags don’t exist (or are not string-typed) in the LaunchDarkly project/environment for your `LD_SDK_KEY`. Create them with Terraform, then the daemon will update `.env` within a second of the SSE update.

## Architecture

```mermaid
flowchart LR
  TF["Terraform<br/>(create flags with variations)"] --> LD["LaunchDarkly Platform<br/>(Flags & Variations)"]
  LD -->|SSE stream| Daemon["Python Daemon<br/>ld_env_sync_daemon.py"]
  Config["Config env vars<br/>LD_SDK_KEY, FLAGS, ENV_FILE_PATH,<br/>LD_CONTEXT_KEY/NAME, BACKUP_ENABLED"] --> Daemon
  Daemon -->|evaluate flags| LD
  Daemon -->|write values| ENV[".env"]
  Daemon -. backup before write .-> Backup[".env.YYYYMMDD-HHMMSS"]
  Apps["Downstream services<br/>(read from .env)"] --> ENV
```

### Startup flow

```mermaid
sequenceDiagram
  participant U as User/Env
  participant D as Python Daemon
  participant LD as LaunchDarkly
  participant F as .env File
  U->>D: Export LD_SDK_KEY and run daemon
  D->>LD: Initialize SDK and open SSE stream
  LD-->>D: Send initial flag data
  D->>D: Evaluate configured flags
  D->>F: Backup .env if it exists
  D->>F: Write evaluated values
  D->>LD: Register flag change listeners
  D->>D: Wait for events (debounced)
```

### Flag change flow

```mermaid
sequenceDiagram
  participant LD as LaunchDarkly
  participant D as Python Daemon
  participant F as .env File
  participant Apps as Downstream Services
  LD-->>D: Flag change event via SSE
  D->>D: Debounce 400ms
  D->>LD: Evaluate all managed flags
  D->>F: Backup .env with timestamp
  D->>F: Write updated flag values
  Apps->>F: Read values on next reload
```


