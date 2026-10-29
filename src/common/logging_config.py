import json
import logging
import sys
from dataclasses import dataclass
from datetime import timezone, datetime
from logging import LoggerAdapter, Logger
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Context:
    tracking_id: str
    object_id: str
    business_id: str
    logger_adapter: LoggerAdapter

    @staticmethod
    def configure_context(
            tracking_id: str,
            object_id: str,
            business_id: str,
            logger: Logger
    ) -> Context:

        required = dict(
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id
        )

        missing = [
            k for k in required.keys() if not required.get(k)
        ]

        if missing:
            raise ValueError(
                f"Missing required fields: {missing}"
            )

        if not logger:
            raise ValueError(
                "Logger cannot be None! Provide logger"
            )

        adapter = logging.LoggerAdapter(
            logger=logger,
            extra=required,
            merge_extra=True
        )
        return Context(
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id,
            logger_adapter=adapter
        )

class JsonFormatter(logging.Formatter):
    def format(
            self,
            record
    )-> str:

        built_in_attrs = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        }

        log: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "msg": record.msg,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in built_in_attrs:
                log[key] = value

        return json.dumps(log)

class LoggingSetup:
    @staticmethod
    def setup_logging(
            file_path: Path,
            logger_name: str,
            logger_level: int = logging.INFO,
            console_string_format: str = "[%(asctime)s][%(levelname)s][%(step)s]|%(message)s",
            console_date_format: str = "%Y-%m-%d %H:%M:%S",
            write_mode: str = 'w',
            encoding: str = 'utf-8',
    ) -> logging.Logger:
        console_formatter = logging.Formatter(
            fmt=console_string_format,
            datefmt=console_date_format
        )
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logger_level)
        console_handler.setFormatter(console_formatter)

        file_handler = logging.FileHandler(
            filename=file_path,
            mode=write_mode,
            encoding=encoding
        )
        file_handler.setLevel(logger_level)
        file_handler.setFormatter(JsonFormatter())
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.propagate = False
        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        return logger