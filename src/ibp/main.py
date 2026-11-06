import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from common.database.config import DatabaseConfig, Table
from common.database.env import require_key, load_env
from common.logging.context import bind_log_context
from common.logging.setup import logging_setup, log_level_mapper
from ibp.control_table import ControlTableInstance, mark_control_table_loading

__file_path__ = Path("C:\\Users\\adm.hv1garroda\\PycharmProjects\\ETL-JOBS\\src\\ibp\\.env")

from ibp.reader import read_from_database_to_csv


def run(
        src_database_config: DatabaseConfig,
        tgt_database_config: DatabaseConfig,
        control_table: Table,
        src_table: Table,
        tgt_table: Table,
        control_table_instance: ControlTableInstance,
        logger: logging.Logger,
        csv_file_dir: Path
)->None:
    logger.info(
        msg="RUN_START",
        extra={
            "step": "ORCHESTRATION"
        }
    )
    control_table_instance = mark_control_table_loading(
        database_config=tgt_database_config,
        control_table=control_table,
        control_table_instance=control_table_instance,
        step="control",
        logger=logger
    )

    read_from_database_to_csv(
        src_database_config=src_database_config,
        src_table=src_table,
        dir_path=csv_file_dir,
        logger=logger,
        step="extract"
    )


    logger.info(
        msg="RUN_END",
        extra={
            "step": "ORCHESTRATION"
        }
    )


def main() -> None:
    try:
        load_env(__file_path__)
        src_database_config = DatabaseConfig.from_env(prefix="SRC")
        tgt_database_config = DatabaseConfig.from_env(prefix="TGT")
        control_table = Table.from_env(prefix="TGT_CONTROL")
        src_table = Table.from_env(prefix="SRC")
        tgt_table = Table.from_env(prefix="TGT")
        process_name = require_key(key="PROCESS_NAME")
        tracking_id = str(uuid4())
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        object_id = f"{src_table.table_name}_{timestamp}"
        business_id = f"{tgt_table.table_name}_{timestamp}"
        logger_name = require_key(key="LOGGER_NAME")
        logger_file = Path(require_key(key="LOG_FILE_PATH"))
        log_level = require_key(key="LOG_LEVEL")
        write_mode = require_key(key="LOGGER_WRITE_MODE")
        encoding = require_key(key="LOGGER_ENCODING")
        csv_file_dir = Path(require_key(key="CSV_FILE_DIR"))
        control_table_instance = ControlTableInstance.create(
            table=tgt_table,
            process_name=process_name,
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id
        )

        bind_log_context(
            timestamp=timestamp,
            object_id=object_id,
            business_id=business_id
        )

        logger = logging_setup(
            logger_name=logger_name,
            file_path=logger_file,
            handlers=None,
            level=log_level_mapper(log_level),
            write_mode=write_mode,
            encoding=encoding
        )

        run(
            src_database_config=src_database_config,
            tgt_database_config=tgt_database_config,
            control_table=control_table,
            src_table=src_table,
            tgt_table=tgt_table,
            control_table_instance=control_table_instance,
            logger=logger,
            csv_file_dir=csv_file_dir
        )

    except Exception:
        raise


main()
