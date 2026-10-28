from dataclasses import dataclass
from datetime import datetime
from ibp.table_staus_enum import ControlTableAllowedStates

@dataclass
class ControlTableStateRecord:
    table_schema: str
    table_name: str
    status: ControlTableAllowedStates
    last_update: datetime
    last_success_at: datetime
    last_failure_at: datetime
    status_changed_at: datetime
    process_name: str
    tracking_id: str
    object_id: str
    business_id: str
    records_inserted: int
    records_rejected: int