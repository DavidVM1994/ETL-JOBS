from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from ibp.databaseconfig import DatabaseConfig


@dataclass(frozen=True)
class ControlTable:
    table_schema: str
    table_name: str
    state: int
    last_update: datetime
    state_changed_at: datetime
    last_success_at: datetime
    last_failure_at: datetime
    process_name: str
    tracking_id: str
    object_id: str
    business_id: str
    records_inserted: int
    records_rejected: int
    message: str
    logger: Logger
    databaseConfig: DatabaseConfig

    def update_control_table(self)-> ControlTable:
        ...