import struct
import time
import pyodbc
from enum import IntEnum
from typing import Any
from dataclasses import dataclass
from logging import Logger
from datetime import datetime, timezone, timedelta
from common.database.config import DatabaseConfig, Table


class ControlTableStates(IntEnum):
    READY = 0
    LOADING = 1
    IMPORT = 2
    SUCCESS = 3
    FREEZE = 4


@dataclass
class ControlTableInstance:
    table: Table
    status: ControlTableStates | None
    last_update: datetime | None
    last_success_at: datetime | None
    status_changed_at: datetime | None
    last_failure_at: datetime | None
    process_name: str | None
    tracking_id: str | None
    object_id: str | None
    business_id: str | None
    records_inserted: int | None
    records_rejected: int | None
    message: str | None

    @classmethod
    def create(
            cls,
            table: Table,
            process_name: str,
            tracking_id: str,
            object_id: str,
            business_id: str
    ) -> ControlTableInstance:
        return cls(
            table=table,
            status=None,
            last_update=None,
            status_changed_at=None,
            last_failure_at=None,
            last_success_at=None,
            process_name=process_name,
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id,
            records_inserted=None,
            records_rejected=None,
            message=None
        )


def handle_datetimeoffset(value):
    tup = struct.unpack("<6hI2h", value)
    return datetime(tup[0], tup[1], tup[2], tup[3], tup[4], tup[5], tup[6] // 1000,
                    timezone(timedelta(hours=tup[7], minutes=tup[8])))


def lookup_control_table(
        cursor: pyodbc.Cursor,
        control_table: Table,
        table: Table,
        step: str,
        logger: Logger
) -> pyodbc.Row | None:
    """Method looks up the control table for the target table using table_schema and table_name.

    If no record is found, a None value is returned."""

    fq_table_name = f"{table.table_schema}.{table.table_name}"
    try:
        logger.info(
            msg="CONTROL_TABLE_LOOKUP_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        sql = f"SELECT * FROM {control_table.table_schema}.{control_table.table_name} WHERE table_schema = ? AND table_name = ?;"
        params = (
            table.table_schema,
            table.table_name
        )
        record = cursor.execute(
            sql,
            params
        ).fetchone()

        logger.info(
            msg="CONTROL_TABLE_LOOKUP_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "table_status": (record.status if record else None)
            }
        )
        return record
    except Exception:
        logger.exception(
            msg="CONTROL_TABLE_LOOKUP_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise


def set_control_table_status_loading(
        cursor: pyodbc.Cursor,
        control_table: Table,
        table: Table,
        process_name: str,
        tracking_id: str,
        object_id: str,
        business_id: str,
        step: str,
        logger: Logger,
        message: str | None

) -> None:
    """Method updates the control table status column to 1=LOADING for the target table"""

    fq_table_name = f"{table.table_schema}.{table.table_name}"
    try:

        logger.info(
            msg="CONTROL_TABLE_SET_LOADING_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        update_sql = f"""
            UPDATE {control_table.table_schema}.{control_table.table_name}
            SET status = {ControlTableStates.LOADING.value}, last_update = ?, status_changed_at = ?, process_name = ?, tracking_id = ?, object_id = ?, business_id = ?, message = ?
            WHERE table_schema = ? AND table_name = ?"""
        timestamp = datetime.now(tz=timezone.utc)
        update_params = (
            timestamp,
            timestamp,
            process_name,
            tracking_id,
            object_id,
            business_id,
            message,
            table.table_schema,
            table.table_name
        )
        updated_records_number = cursor.execute(
            update_sql,
            update_params
        ).rowcount

        logger.info(
            msg="CONTROL_TABLE_SET_LOADING_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "record_count": updated_records_number
            }
        )

    except Exception:
        logger.exception(
            msg="CONTROL_TABLE_SET_LOADING_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise


def set_control_table_status_ready(
        cursor: pyodbc.Cursor,
        control_table: Table,
        table: Table,
        step: str,
        records_inserted: int | None,
        records_rejected: int | None,
        logger: Logger
) -> None:
    """Method updates the control table status column to 0=READY for the target table"""

    fq_table_name = f"{table.table_schema}.{table.table_name}"
    try:
        records_inserted = records_inserted if records_inserted is not None else 0
        records_rejected = records_rejected if records_rejected is not None else 0

        logger.info(
            msg="CONTROL_TABLE_SET_READY_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        sql = f"""
            UPDATE {control_table.table_schema}.{control_table.table_name}
            SET status = {ControlTableStates.READY.value}, last_update = ?, status_changed_at = ?, last_success_at = ?, records_inserted = ?, records_rejected = ?
            WHERE table_schema = ? AND table_name = ?"""
        timestamp = datetime.now(tz=timezone.utc)
        update_params = (
            timestamp,
            timestamp,
            timestamp,
            records_inserted,
            records_rejected,
            table.table_schema,
            table.table_name
        )
        updated_records_number = cursor.execute(
            sql,
            update_params
        ).rowcount

        logger.info(
            msg="CONTROL_TABLE_SET_READY_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "record_count": updated_records_number
            }
        )

    except Exception:
        logger.exception(
            msg="CONTROL_TABLE_SET_READY_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise


def mark_control_table_loading(
        database_config: DatabaseConfig,
        control_table_instance: ControlTableInstance,
        control_table: Table,
        step: str,
        logger: Logger
) -> ControlTableInstance:
    """ Method orchestrates the following operations:

    1) Reads the input table status in the control table; If no records is present for the table an exception is raised. If table status is not READY, LOADING an exception is raised.

    2) Updates the input table status to 1 LOADING in the control table; if it fails an exception is raised.

    3) Retrieves the control table record for the target table to check the update and maps it to DTO.
    """
    table_schema = control_table_instance.table.table_schema
    table_name = control_table_instance.table.table_name
    fq_table_name = f"{table_schema}.{table_name}"

    required: dict[str, Any] = {
        "control_table_schema": control_table.table_schema,
        "control_table_name": control_table.table_name,
        "table_schema": table_schema,
        "table_name": table_name,
        "process_name": control_table_instance.process_name,
        "tracking_id": control_table_instance.tracking_id,
        "object_id": control_table_instance.object_id,
        "business_id": control_table_instance.business_id
    }

    try:

        logger.info(
            msg="CONTROL_TABLE_MARK_LOADING_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        missing = [key for key in required.keys() if not required.get(key)]

        if missing:
            raise RuntimeError(
                f"Missing required input fields: {missing}"
            )

        start_time = time.perf_counter()
        with pyodbc.connect(
                driver=database_config.driver,
                server=database_config.host,
                database=database_config.dbname,
                encrypt="yes",
                trustservercertificate="yes",
                uid=database_config.username,
                pwd=database_config.password,
                autocommit=False
        ) as conn:
            conn.add_output_converter(-155, handle_datetimeoffset)
            with conn.cursor() as cursor:
                row = lookup_control_table(
                    cursor=cursor,
                    control_table=control_table,
                    table=control_table_instance.table,
                    step=step,
                    logger=logger
                )

                if row is None:
                    raise RuntimeError(
                        f"No record found in the control table for target table: {fq_table_name}"
                    )

                if row.status not in (ControlTableStates.READY, ControlTableStates.LOADING):
                    raise RuntimeError(
                        "Table status in control table is not 0 (READY) or 1 (LOADING)! Flow cannot proceed!"
                    )

                set_control_table_status_loading(
                    cursor=cursor,
                    control_table=control_table,
                    table=control_table_instance.table,
                    process_name=control_table_instance.process_name,
                    tracking_id=control_table_instance.tracking_id,
                    object_id=control_table_instance.object_id,
                    business_id=control_table_instance.business_id,
                    message=control_table_instance.message,
                    step=step,
                    logger=logger
                )

                retrieved = lookup_control_table(
                    cursor=cursor,
                    control_table=control_table,
                    table=control_table_instance.table,
                    step=step,
                    logger=logger
                )

                if retrieved is None:
                    raise RuntimeError(
                        f"Failed to retrieve control table record for table: {fq_table_name}!"
                    )
            conn.commit()
        end_time = time.perf_counter()
        logger.info(
            msg="CONTROL_TABLE_MARK_LOADING_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "duration_s": round(end_time - start_time, 2)
            }

        )
        return ControlTableInstance(
            table=Table(
                table_schema=retrieved.table_schema,
                table_name=retrieved.table_name
            ),
            status=retrieved.status,
            last_update=retrieved.last_update,
            status_changed_at=retrieved.status_changed_at,
            last_success_at=retrieved.last_success_at,
            last_failure_at=retrieved.last_failure_at,
            process_name=retrieved.process_name,
            tracking_id=retrieved.tracking_id,
            object_id=retrieved.object_id,
            business_id=retrieved.business_id,
            records_inserted=retrieved.records_inserted,
            records_rejected=retrieved.records_rejected,
            message=retrieved.message,
        )
    except Exception:
        logger.exception(
            msg="CONTROL_TABLE_MARK_LOADING_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise


def mark_control_table_ready(
        database_config: DatabaseConfig,
        control_table_instance: ControlTableInstance,
        control_table: Table,
        step: str,
        logger: Logger
) -> None:
    """ Method Orchestrates the following operations:

    1) Updates the control table status column for the target table to 0=READY; If the update fails an exception is raised

    2) Reads the control table and checks that the update was successful, otherwise raises an exception
    """
    table_schema = control_table_instance.table.table_schema
    table_name = control_table_instance.table.table_name
    fq_table_name = f"{table_schema}.{table_name}"

    required: dict[str, Any] = {
        "control_table_schema": control_table.table_schema,
        "control_table_name": control_table.table_name,
        "table_schema": table_schema,
        "table_name": table_name
    }

    try:

        logger.info(
            msg="CONTROL_TABLE_MARK_READY_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        missing = [key for key in required.keys() if not required.get(key)]

        if missing:
            raise RuntimeError(
                f"Missing required input fields: {missing}"
            )

        start_time = time.perf_counter()
        with pyodbc.connect(
                driver=database_config.driver,
                server=database_config.host,
                database=database_config.dbname,
                encrypt="yes",
                trustservercertificate="yes",
                uid=database_config.username,
                pwd=database_config.password,
                autocommit=False
        ) as conn:
            conn.add_output_converter(-155, handle_datetimeoffset)
            with conn.cursor() as cursor:

                set_control_table_status_ready(
                    cursor=cursor,
                    control_table=control_table,
                    table=control_table_instance.table,
                    step=step,
                    logger=logger,
                    records_inserted=control_table_instance.records_inserted,
                    records_rejected=control_table_instance.records_rejected
                )

                retrieved = lookup_control_table(
                    cursor=cursor,
                    control_table=control_table,
                    table=control_table_instance.table,
                    step=step,
                    logger=logger
                )

                if retrieved is None:
                    raise RuntimeError(
                        f"Failed to retrieve control table record for table: {fq_table_name}!"
                    )
                if retrieved.status != ControlTableStates.READY:
                    raise RuntimeError(
                        f"Failed to updated control table record for table: {fq_table_name}!"
                    )
            conn.commit()
        end_time = time.perf_counter()
        logger.info(
            msg="CONTROL_TABLE_MARK_READY_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "duration_s": round(end_time - start_time, 2)
            }

        )

    except Exception:
        logger.exception(
            msg="CONTROL_TABLE_MARK_READY_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise
