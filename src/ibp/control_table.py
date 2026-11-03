import time
from typing import Any

import pyodbc
from dataclasses import dataclass
from logging import Logger
from datetime import datetime, timezone
from common.database.databaseconfig import DatabaseConfig
from ibp.table_staus_enum import ControlTableStates

@dataclass
class ControlTableInstance:
    table_schema: str
    table_name: str
    status: ControlTableStates
    last_update: datetime
    status_changed_at: datetime
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


def lookup_control_table(
        cursor: pyodbc.Cursor,
        control_table_schema: str,
        control_table_name: str,
        table_schema: str,
        table_name: str,
        step: str,
        logger: Logger
) -> pyodbc.Row | None:
    """Method looks up the control table for the given table_schema and table_name. If the given table has no record in the control table, an exception is raised."""
    fq_table_name = f"{table_schema}.{table_name}"
    try:
        logger.info(
            msg="CONTROL_TABLE_LOOKUP_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        sql = f"SELECT * FROM {control_table_schema}.{control_table_name} WHERE table_schema = ? AND table_name = ?;"
        params = (
            table_schema,
            table_name
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
                "record_count": cursor.rowcount,
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

def update_control_table_status_to_loading(
        cursor: pyodbc.Cursor,
        control_table_schema:str,
        control_table_name: str,
        table_schema: str,
        table_name: str,
        step: str,
        logger: Logger
) -> None:
    """Method update the status in the control table for the given table; if the record does not exist, it raises an exception."""

    try:
        fq_table_name = f"{table_schema}.{table_name}"

        logger.info(
            msg="SET_TABLE_STATUS_TO_LOADING_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        update_sql = f"""
            UPDATE {control_table_schema}.{control_table_name}
            SET status = {ControlTableStates.LOADING}, last_update = ?, status_changed_at = ?, process_name = ?, tracking_id = ?, object_id = ?, business_id = ?, message = ?
            WHERE table_schema = ? AND table_name = ?"""
        timestamp = datetime.now(tz=timezone.utc)
        update_params = (timestamp, timestamp, table_schema, table_name)
        updated_records_number = cursor.execute(
            update_sql,
            update_params
        ).rowcount

        logger.info(
            msg="SET_TABLE_STATUS_TO_LOADING_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "record_count": updated_records_number
            }
        )

    except Exception:
        logger.exception(
            msg="SET_TABLE_STATUS_TO_LOADING_EXCEPTION",
            extra={
                "step": step,
                "table": f"{table_schema}.{table_name}"
            }
        )
        raise


def update_control_table_status_to_ready(
        cursor: pyodbc.Cursor,
        control_table_schema: str,
        control_table_name: str,
        table_schema: str,
        table_name: str,
        step: str,
        records_inserted: int,
        records_rejected: int,
        logger: Logger
) -> None:
    """Method update the status to ready(successful flow execution) in the control table for the given table; if the record does not exist, it raises an exception."""

    try:
        fq_table_name = f"{table_schema}.{table_name}"

        logger.info(
            msg="SET_TABLE_STATUS_TO_READY_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        
        sql = f"""
            UPDATE {control_table_schema}.{control_table_name}
            SET status = {ControlTableStates.READY}, last_update = ?, status_changed_at = ?, last_success_at = ?, records_inserted = ?, records_rejected = ?
            WHERE table_schema = ? AND table_name = ?"""
        timestamp = datetime.now(tz=timezone.utc)
        update_params = (timestamp, timestamp, timestamp, records_inserted, records_rejected, table_schema, table_name)
        updated_records_number = cursor.execute(
            sql,
            update_params
        ).rowcount

        logger.info(
            msg="SET_TABLE_STATUS_TO_READY_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "record_count": updated_records_number
            }
        )

    except Exception:
        logger.exception(
            msg="SET_TABLE_STATUS_TO_READY_EXCEPTION",
            extra={
                "step": step,
                "table": f"{table_schema}.{table_name}"
            }
        )
        raise

def update_control_table_status(
        database_config: DatabaseConfig,
        control_table_instance: ControlTableInstance,
        control_table_schema: str,
        control_table_name: str,
        step: str,
        logger: Logger
)-> ControlTableInstance:
    """ Methods orchestrate the following operations:

    1) Read the input table status in the control table; If no records is present for the table an exception is raised. If table status is not 0, 1 an exception is raised.

    2) Update the input table status to 1 (Loading) in the control table; if updated fails an exception is raised.

    3) Retrieve the control table record corresponding to the given table and return a DTO
    """
    table_schema = control_table_instance.table_schema
    table_name = control_table_instance.table_name
    fq_table_name = f"{table_schema}.{table_name}"

    required: dict[str, Any] = {
        "control_table_schema": control_table_schema,
        "control_table_name": control_table_name,
        "table_schema": table_schema,
        "table_name": table_name,
        "process_name": control_table_instance.process_name,
        "tracking_id": control_table_instance.tracking_id,
        "object_id": control_table_instance.object_id,
        "business_id": control_table_instance.business_id
    }

    try:

        logger.info(
            msg="UPDATE_CONTROL_TABLE_STATUS_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )

        missing = [key for key in required.keys() if not required.get(key)]

        if missing:
            raise RuntimeError(f"Missing required fields: {missing}")

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
            with conn.cursor() as cursor:
                row = lookup_control_table(
                    cursor=cursor,
                    control_table_schema=control_table_schema,
                    control_table_name=control_table_name,
                    table_schema=table_schema,
                    table_name=table_name,
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

                update_control_table_status_to_loading(
                    cursor=cursor,
                    control_table_schema=control_table_schema,
                    control_table_name=control_table_name,
                    table_schema=table_schema,
                    table_name=table_name,
                    step=step,
                    logger=logger
                )

                retrieved = lookup_control_table(
                    cursor=cursor,
                    control_table_schema=control_table_schema,
                    control_table_name=control_table_name,
                    table_schema=table_schema,
                    table_name=table_name,
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
            msg="UPDATE_CONTROL_TABLE_STATUS_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "duration_s": round(end_time - start_time, 2)
            }

        )
        return ControlTableInstance(
            table_schema=retrieved.table_schema,
            table_name=retrieved.table_name,
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
            msg="UPDATE_CONTROL_TABLE_STATUS_EXCEPTION",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        raise