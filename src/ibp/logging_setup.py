import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record)-> str:
        log = {}
        for key, value in record.__dict__.items():
            if not value:
                log[key] = value
        if record.exc_info:
            log['exc_info'] = record.exc_info
        return json.dumps(log)

def configure_logger(logger_name: str, logger_level: int) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)

    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger