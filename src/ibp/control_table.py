import time
import pyodbc
from logging import Logger
from datetime import datetime, timezone
from common.database.databaseconfig import DatabaseConfig
from ibp.table_staus_enum import ControlTableAllowedStates

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
        if not cursor:
            raise RuntimeError(
                "Lookup failed! cursor cannot be None!"
            )
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
) -> int:
    """Method update the status in the control table for the given table; if the record does not exist, it raises an exception."""

    try:
        if not table_schema or not table_name:
            raise RuntimeError(
                "table_schema and table_name cannot be None!"
            )
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
            SET status = 1, last_update = ?, status_changed_at = ?
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
        return updated_records_number
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
) -> int:
    """Method update the status to ready(successful flow execution) in the control table for the given table; if the record does not exist, it raises an exception."""

    try:
        if not table_schema or not table_name:
            raise RuntimeError(
                "table_schema and table_name cannot be None!"
            )
        fq_table_name = f"{table_schema}.{table_name}"

        logger.info(
            msg="SET_TABLE_STATUS_TO_READY_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        update_sql = f"""
            UPDATE {control_table_schema}.{control_table_name}
            SET status = 0, last_update = ?, status_changed_at = ?, last_success_at = ?, records_inserted = ?, records_rejected = ?
            WHERE table_schema = ? AND table_name = ?"""
        timestamp = datetime.now(tz=timezone.utc)
        update_params = (timestamp, timestamp, timestamp, records_inserted, records_rejected, table_schema, table_name)
        updated_records_number = cursor.execute(
            update_sql,
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
        return updated_records_number
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
        control_table_schema: str,
        control_table_name: str,
        table_schema: str,
        table_name: str,
        step: str,
        logger: Logger
)-> None:
    """Methods orchestrate the following operations: read the given table control status if exists, update the control table status to working"""

    fq_table_name = f"{table_schema}.{table_name}"
    try:
        logger.info(
            msg="UPDATE_CONTROL_TABLE_STATUS_START",
            extra={
                "step": step,
                "table": fq_table_name
            }
        )
        start_time = time.perf_counter()
        with pyodbc.connect(
                driver="ODBC Driver 18 for SQL Server",
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
                        f"Failed to retrieve control table record for table {fq_table_name}!"
                    )
                if row.status not in (ControlTableAllowedStates.READY, ControlTableAllowedStates.LOADING):
                    raise RuntimeError(
                        f"Status in control table is not {ControlTableAllowedStates.READY.value} (READY) or {ControlTableAllowedStates.LOADING.value} (LOADING) for table: {fq_table_name}"
                    )
                if update_control_table_status_to_loading(
                        cursor=cursor,
                        control_table_schema=control_table_schema,
                        control_table_name=control_table_name,
                        table_schema=table_schema,
                        table_name=table_name,
                        step=step,
                        logger=logger
                ) == 0:
                    raise RuntimeError(
                        "Failed to update table status to loading in control table!"
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

        end_time = time.perf_counter()
        logger.info(
            msg="UPDATE_CONTROL_TABLE_STATUS_END",
            extra={
                "step": step,
                "table": fq_table_name,
                "duration_s": round(end_time - start_time, 2)
            }
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