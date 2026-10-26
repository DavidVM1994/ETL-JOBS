import logging
from dataclasses import dataclass
from logging import LoggerAdapter, Logger

@dataclass(frozen=True)
class Context:
    tracking_id: str
    object_id: str
    business_id: str
    logger: LoggerAdapter

    @staticmethod
    def create(tracking_id: str, object_id: str, business_id: str, logger: Logger) -> Context:
        adapter = logging.LoggerAdapter(
            logger=logger,
            extra={
                "tracking_id": tracking_id,
                "business_id": business_id,
                "object_id": object_id
            },
            merge_extra=True
        )
        return Context(
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id ,
            logger=adapter
        )