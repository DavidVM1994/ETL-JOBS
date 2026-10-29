import logging
from common.logging_config import Context, LoggingSetup
from pathlib import Path

class EtlOrchestrator:
    def __init__(
            self,
            ctx: Context,
            control_table_schema: str,
            control_table_name: str,
            control_table_state_schema: str,
            control_table_state_name: str

    )->None:
        self.ctx = ctx
        self.control_table_schema = control_table_schema
        self.control_table_name = control_table_name
        self.control_table_state_schema = control_table_state_schema
        self.control_table_state_name = control_table_state_name

    def run(self, table_schema: str, table_name: str, step: str)->None:

        try:
            ...
        except Exception:
            raise

def main()->None:


    logger = LoggingSetup.setup_logging(
        logger_name="ibp",
        logger_level=logging.INFO,
        file_path=Path(__file__).parent.absolute()
    )

    context = Context.configure_context(
        tracking_id="",
        object_id="",
        business_id="",
        logger=logger
    )
