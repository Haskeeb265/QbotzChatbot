# observability/logger.py
import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import json
from config.settings import settings


class StructuredLogger:

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        self.name = name

        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):

        handler = logging.StreamHandler(sys.stdout)

        if settings.ENVIRONMENT == "production":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(HumanReadableFormatter())

        self.logger.addHandler(handler)

    def info(self, event: str, **kwargs):

        self._log("INFO", event, kwargs)

    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self._log("ERROR", event, kwargs)

    def debug(self, event: str, **kwargs):
        self._log("DEBUG", event, kwargs)

    def warning(self, event: str, **kwargs):
        self._log("WARNING", event, kwargs)

    def _log(self, level: str, event: str, context: Dict[str, Any]):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": self.name,
            "event": event,
            **context,  # Merge in the extra context
        }

        log_method = getattr(self.logger, level.lower())
        log_method(event, extra=log_data)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": getattr(record, "timestamp", ""),
            "level": record.levelname,
            "component": getattr(record, "component", ""),
            "event": record.getMessage(),
        }

        # Add all extra fields passed via logger.info(..., field=value)
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "timestamp",
                "component",
            ]:
                log_obj[key] = value

        return json.dumps(log_obj)


class HumanReadableFormatter(logging.Formatter):

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        timestamp = getattr(record, "timestamp", datetime.utcnow().isoformat())
        component = getattr(record, "component", "unknown")
        event = record.getMessage()

        # Collect extra fields
        extras = []
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "timestamp",
                "component",
                "event",
            ]:
                extras.append(f"{key}={value}")

        extras_str = " ".join(extras)

        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        return f"{color}[{timestamp[:19]}] {record.levelname:8} [{component}] {event} {extras_str}{reset}"


def get_logger(component_name: str) -> StructuredLogger:
    return StructuredLogger(component_name)
