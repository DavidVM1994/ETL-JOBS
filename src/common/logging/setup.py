import json
import logging
import sys
from pathlib import Path
from common.logging.context import log_context
from datetime import datetime, timezone

class ContextFilter(logging.Filter):
    """Class implements the logging.Filter protocol, and its filter implementation maps all the content of the log_context onto
        the log record, if not already present."""

    def filter(self, record):
        for key, value in log_context.get().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True

class JsonLogFormatter(logging.Formatter):
    """Class implements the logging.Formatter protocol, implements by contract the format method which defines the mapping rules for the log message"""

    def format(self, record)->str:

        built_in = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        }

        log = {
            "timestamp": datetime.fromtimestamp(
                timestamp=record.created,
                tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if not key in built_in and not key in log:
                log[key] = value

        return json.dumps(log, ensure_ascii=False, default=str)

def logging_setup(
        logger_name: str,
        file_path: Path | None,
        handlers: list[logging.Handler] | None,
        level: int = logging.INFO,
        write_mode: str = 'a',
        encoding: str = 'utf-8'
) -> logging.Logger:
    """Methods set up a logger with the specified name, level and handlers. I also exposed (with sensible defaults) file format parameters(write_mode, encoding)
        to allow more flexibility during testing"""

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    context_filter = ContextFilter()

    if not handlers:
        handlers = [create_console_handler(level)]
        if file_path:
            handlers.append(
                create_json_file_handler(level, file_path, write_mode, encoding, JsonLogFormatter())
            )

    for handler in handlers:
            logger.addHandler(handler)
    logger.addFilter(filter=context_filter)
    return logger

def create_console_handler(level: int) -> logging.Handler:
    """This is a helper method that creates a default console handler from the input log level"""

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level=level)
    handler.setFormatter(formatter)
    return handler

def create_json_file_handler(level: int, file_path: Path, write_mode: str, encoding: str, logging_formatter: logging.Formatter) -> logging.Handler:
    """This is a helper method that creates a default file handler with the specified format, path, write_mode and encoding. I intentionally exposed the file formatter as input
        parameter for flexibility, but guarded it with a JSON default formatter"""

    formatter = logging_formatter
    if not formatter:
        formatter =JsonLogFormatter()

    handler = logging.FileHandler(
        filename=file_path,
        mode=write_mode,
        encoding=encoding
    )
    handler.setLevel(level=level)
    handler.setFormatter(formatter)
    return handler

def log_level_mapper(level:str) -> int:
    match level:
        case "DEBUG":
            return logging.DEBUG
        case "INFO":
            return logging.INFO
        case "WARNING":
            return logging.WARNING
        case "ERROR":
            return logging.ERROR
    raise ValueError(
        f"Invalid log level:{level}"
    )

