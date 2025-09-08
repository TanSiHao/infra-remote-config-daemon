#!/usr/bin/env python3
"""
LaunchDarkly → .env Sync Daemon (Python)

This daemon listens for LaunchDarkly flag changes via the server-side SDK's streaming
connection (SSE) and keeps a local .env file updated with evaluated flag values.

Configuration (via environment variables):
  - LD_SDK_KEY           (required) LaunchDarkly server-side SDK key
  - FLAGS                (optional) Comma-separated flag keys to manage
                                      default: SAMPLE_API_URL,SAMPLE_SERVICE_URL,SAMPLE_APP_URL
  - ENV_FILE_PATH        (optional) Path to .env file (default: ./.env)
  - BACKUP_ENABLED       (optional) true/false to enable timestamped backups (default: true)
  - LOG_LEVEL            (optional) DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
  - DEBOUNCE_MS          (optional) Milliseconds to debounce rapid updates (default: 400)
  - LD_CONTEXT_KEY       (optional) Context key used for evaluation (default: sample-daemon)
  - LD_CONTEXT_NAME      (optional) Human-readable name for context (default: Daemon)

Run:
  python ld_env_sync_daemon.py

Requires packages:
  launchdarkly-server-sdk
  python-dotenv
"""

import json
import logging
import os
import shutil
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import ldclient
from ldclient.config import Config
from ldclient.context import Context
from dotenv import set_key


@dataclass
class DaemonConfig:
    sdk_key: str
    flag_keys: List[str]
    env_file_path: str
    backup_enabled: bool
    log_level: str
    debounce_ms: int
    context_key: str
    context_name: str


def load_config_from_env() -> DaemonConfig:
    sdk_key = os.getenv("LD_SDK_KEY", "").strip()
    default_flags = [
        "SAMPLE_API_URL",
        "SAMPLE_SERVICE_URL",
        "SAMPLE_APP_URL",
    ]
    flags_env = os.getenv("FLAGS", ",".join(default_flags))
    flag_keys = [k.strip() for k in flags_env.split(",") if k.strip()]
    env_file_path = os.getenv("ENV_FILE_PATH", ".env")
    backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    debounce_ms = int(os.getenv("DEBOUNCE_MS", "400"))
    context_key = os.getenv("LD_CONTEXT_KEY", "sample-daemon")
    context_name = os.getenv("LD_CONTEXT_NAME", "Daemon")
    return DaemonConfig(
        sdk_key=sdk_key,
        flag_keys=flag_keys,
        env_file_path=env_file_path,
        backup_enabled=backup_enabled,
        log_level=log_level,
        debounce_ms=debounce_ms,
        context_key=context_key,
        context_name=context_name,
    )


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class Debouncer:
    """Simple thread-safe debouncer to coalesce rapid events."""

    def __init__(self, debounce_ms: int, action):
        self._debounce_seconds = max(0, debounce_ms) / 1000.0
        self._action = action
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def trigger(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._run)
            self._timer.daemon = True
            self._timer.start()

    def _run(self) -> None:
        try:
            self._action()
        except Exception as exc:  # noqa: BLE001
            logging.exception("Debounced action failed: %s", exc)

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


def ensure_file_permissions_owner_rw(path: str) -> None:
    try:
        os.chmod(path, 0o600)
    except Exception:
        logging.debug("Could not set file permissions to 600 for %s", path)


def backup_env_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{path}.{timestamp}"
    shutil.copy2(path, backup_path)
    logging.info("Backed up %s to %s", path, backup_path)
    return backup_path


def write_env_values(path: str, values: Dict[str, str], backup_enabled: bool) -> None:
    if backup_enabled and os.path.exists(path):
        backup_env_file(path)
    # Write values using python-dotenv set_key to update or add keys
    for key, value in values.items():
        set_key(path, key, str(value), quote_mode="never")
    ensure_file_permissions_owner_rw(path)
    logging.info("Updated %s with %d key(s)", path, len(values))


def build_context(context_key: str, context_name: str) -> Context:
    builder = Context.builder(context_key)
    builder.name(context_name)
    return builder.build()


class EnvSyncDaemon:
    def __init__(self, config: DaemonConfig):
        self._config = config
        self._stop_event = threading.Event()
        self._client = None  # type: ignore[assignment]
        self._context: Context | None = None
        self._debouncer = Debouncer(config.debounce_ms, self._sync_all_flags_to_env)

    def start(self) -> None:
        if not self._config.sdk_key:
            logging.critical("LD_SDK_KEY is required. Set it in the environment and retry.")
            sys.exit(2)

        logging.info("Starting LaunchDarkly client and initializing streaming connection…")
        ldclient.set_config(
            Config(
                sdk_key=self._config.sdk_key,
                stream=True,
                send_events=True,
            )
        )
        self._client = ldclient.get()
        self._context = build_context(self._config.context_key, self._config.context_name)

        # Wait a short period for initial data; proceed even if not ready to avoid deadlock
        self._wait_for_initialization(max_wait_seconds=10)

        # Initial sync
        logging.info("Performing initial flag evaluation and .env sync…")
        self._sync_all_flags_to_env()

        # Register listeners to react to changes
        self._register_flag_listeners()

        # Keep running until stopped
        self._run_loop()

    def _wait_for_initialization(self, max_wait_seconds: int) -> None:
        if self._client is None:
            return
        waited = 0
        while waited < max_wait_seconds:
            try:
                if self._client.is_initialized():
                    logging.info("LaunchDarkly client initialized.")
                    return
            except Exception:
                pass
            time.sleep(0.5)
            waited += 0.5
        logging.warning("LaunchDarkly client did not report initialized after %ss; continuing.", max_wait_seconds)

    def _register_flag_listeners(self) -> None:
        if self._client is None or self._context is None:
            return

        try:
            flag_tracker = self._client.flag_tracker
        except Exception as exc:  # noqa: BLE001
            logging.warning("Flag tracker not available; will rely on periodic syncs. %s", exc)
            return

        def on_value_change(_event) -> None:
            logging.debug("Flag value change event received; scheduling debounced sync…")
            self._debouncer.trigger()

        for flag_key in self._config.flag_keys:
            try:
                flag_tracker.add_flag_value_change_listener(flag_key, self._context, on_value_change)
                logging.info("Registered change listener for flag '%s'", flag_key)
            except Exception as exc:  # noqa: BLE001
                logging.error("Failed to register listener for flag '%s': %s", flag_key, exc)

    def _evaluate_all_flags(self) -> Dict[str, str]:
        if self._client is None or self._context is None:
            return {}
        values: Dict[str, str] = {}
        for flag_key in self._config.flag_keys:
            try:
                # Default value as empty string if flag missing/mismatched type
                val = self._client.variation(flag_key, self._context, "")
                values[flag_key] = str(val)
            except Exception as exc:  # noqa: BLE001
                logging.warning("Failed to evaluate flag '%s': %s", flag_key, exc)
                values[flag_key] = ""
        return values

    def _sync_all_flags_to_env(self) -> None:
        values = self._evaluate_all_flags()
        if not values:
            logging.warning("No flag values evaluated; skipping .env write.")
            return
        write_env_values(self._config.env_file_path, values, self._config.backup_enabled)

    def _run_loop(self) -> None:
        logging.info("Daemon is running. Press Ctrl+C to stop.")

        def handle_signal(signum, _frame):
            logging.info("Received signal %s; shutting down…", signum)
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        try:
            while not self._stop_event.is_set():
                time.sleep(1.0)
        finally:
            self._shutdown()

    def stop(self) -> None:
        self._stop_event.set()

    def _shutdown(self) -> None:
        logging.info("Stopping daemon…")
        try:
            self._debouncer.cancel()
        except Exception:
            pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        logging.info("Shutdown complete.")


def main() -> None:
    config = load_config_from_env()
    configure_logging(config.log_level)
    daemon = EnvSyncDaemon(config)
    daemon.start()


if __name__ == "__main__":
    main()


