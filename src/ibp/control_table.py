import time
import pyodbc
from dataclasses import dataclass
from datetime import datetime
from ibp.context import Context
from ibp.databaseconfig import DatabaseConfig
from ibp.table_status import ControlTableStateRecord
from ibp.table_staus_enum import ControlTableAllowedStates

@dataclass(frozen=True)
class EtlControlTableState:
    ctx: Context
    database_config: DatabaseConfig
    control_table_schema: str
    control_table_name: str
    control_table_status_schema: str
    control_table_status_name: str

    def read_control_table(self, cursor: pyodbc.Cursor, table_schema: str, table_name: str, step: str) -> pyodbc.Row | None:
        fq_table_name = f"{table_schema}.{table_name}"
        try:
            if not cursor:
                raise RuntimeError("Cannot access connection cursor!")
            self.ctx.logger.info(
                msg="CONTROL_TABLE_READ_START",
                extra={
                    "step": step,
                    "table": fq_table_name
                }
            )
            read_sql = f"""
                SELECT cts.*, ct.description, ct.system_message 
                FROM {self.control_table_status_schema}.{self.control_table_status_name} AS cts
                INNER JOIN {self.control_table_schema}.{self.control_table_name} AS ct ON ct.status = cts.status
                WHERE cts.table_schema = ? AND cts.table_name = ?"""
            read_params = (table_schema, table_name)
            record = cursor.execute(read_sql, read_params).fetchone()
            self.ctx.logger.info(
                msg="CONTROL_TABLE_READ_END",
                extra={
                    "step": step,
                    "table": fq_table_name,
                    "record_count": cursor.rowcount,
                    "table_status": (record.status if record else None)
                }
            )
            return record
        except Exception:
            self.ctx.logger.exception(
                msg="CONTROL_TABLE_READ_EXCEPTION",
                extra={
                    "step": step,
                    "table": fq_table_name
                }
            )
            raise

    def update_control_table(self, cursor: pyodbc.Cursor, status: ControlTableAllowedStates, table_schema: str, table_name: str, step: str) -> int:
        try:
            if not isinstance(status, ControlTableAllowedStates):
                raise TypeError("Invalid control table status type!")
            if table_schema is None or table_name is None:
                raise RuntimeError("table_schema and table_name cannot be None!")
            fq_table_name = f"{table_schema}.{table_name}"
            self.ctx.logger.info(
                msg="CONTROL_TABLE_STATUS_UPDATE_START",
                extra={
                    "step": step,
                    "table": fq_table_name
                }
            )
            update_sql = f"""
                UPDATE {self.control_table_status_schema}.{self.control_table_status_name}
                SET status = ?, 
                last_update = SYSDATETIMEOFFSET(), 
                status_changed_at = SYSDATETIMEOFFSET()
                WHERE table_schema = ? AND table_name = ?"""
            update_params = (status.value, table_schema, table_name)
            updated_records_number = cursor.execute(update_sql, update_params).rowcount
            self.ctx.logger.info(
                msg="CONTROL_TABLE_STATUS_UPDATE_END",
                extra={
                    "step": step,
                    "table": fq_table_name,
                    "record_count": updated_records_number
                }
            )
            return updated_records_number
        except Exception:
            self.ctx.logger.exception(
                msg="CONTROL_TABLE_STATUS_UPDATE_EXCEPTION",
                extra={
                    "step": step,
                    "table": f"{table_schema}.{table_name}"
                }
            )
            raise
    @staticmethod
    def update_fields(record: ControlTableStateRecord, status: ControlTableAllowedStates, last_update: datetime, status_changed_at: datetime, last_success_at: datetime, last_failure_at: datetime,
                      records_inserted: int | None, records_rejected: int | None) -> ControlTableStateRecord:
        if status is None:
            raise RuntimeError("table control status cannot be set to None!")
        if not isinstance(status, ControlTableAllowedStates):
            raise TypeError("Invalid control table status type!")
        if last_update is None:
            raise RuntimeError("table control last_updated cannot be set to None!")
        if status_changed_at is None:
            raise RuntimeError("table control status_changed_at cannot be set to None!")
        record.status = status
        record.last_update = last_update
        record.status_changed_at = status_changed_at
        record.last_success_at = last_success_at
        record.last_failure_at = last_failure_at
        if records_inserted is not None:
            record.records_inserted = records_inserted
        if records_rejected is not None:
            record.records_rejected = records_rejected
        return record

    def update_control_table_status(self, control_table_state: ControlTableStateRecord, step: str)-> ControlTableStateRecord:
        table_schema = control_table_state.table_schema
        table_name = control_table_state.table_name
        fq_table_name = f"{table_schema}.{table_name}"
        action = ""
        try:
            target_status = control_table_state.status
            if target_status is None:
                raise RuntimeError(
                    "table control status cannot be set to None!"
                )
            if target_status not in (ControlTableAllowedStates.READY, ControlTableAllowedStates.LOADING):
                raise RuntimeError(
                    f"Only table with status in ({ControlTableAllowedStates.READY}, {ControlTableAllowedStates.LOADING}) can be updated!"
                )
            action = target_status.name
            self.ctx.logger.info(
                msg=f"SET_TABLE_CONTROL_STATUS_TO_{action}_START",
                extra={
                    "step": step,
                    "table": fq_table_name
                }
            )
            start_time = time.perf_counter()
            with pyodbc.connect(
                    driver="ODBC Driver 18 for SQL Server",
                    server=self.database_config.host,
                    database=self.database_config.dbname,
                    encrypt="yes",
                    trustservercertificate="yes",
                    uid=self.database_config.username,
                    pwd=self.database_config.password,
                    autocommit=False
            ) as conn:
                with conn.cursor() as cursor:
                    row = self.read_control_table(
                        cursor=cursor,
                        table_schema=table_schema,
                        table_name=table_name,
                        step=step
                    )
                    if row is None:
                        raise RuntimeError(
                            f"Failed to retrieve control table record for table {fq_table_name}!"
                        )
                    retrieved_status = ControlTableAllowedStates(row.status)
                    if retrieved_status not in (ControlTableAllowedStates.READY, ControlTableAllowedStates.LOADING):
                        raise RuntimeError(
                            f"Status in control table is not {ControlTableAllowedStates.READY.value} (READY) or {ControlTableAllowedStates.LOADING.value} (LOADING) for table: {fq_table_name}"
                        )
                    if self.update_control_table(
                            cursor=cursor,
                            status=target_status,
                            table_schema=table_schema,
                            table_name=table_name,
                            step=step
                    ) == 0:
                        raise RuntimeError(
                            "Failed to update table status in control table!"
                        )
                    retrieved = self.read_control_table(
                        cursor=cursor,
                        table_schema=table_schema,
                        table_name=table_name,
                        step=step
                    )
                    if retrieved is None:
                        raise RuntimeError(
                            f"Failed to retrieve control table record for table: {fq_table_name}!"
                        )
                    updated_record = self.update_fields(
                        record = control_table_state,
                        status = ControlTableAllowedStates(retrieved.status),
                        last_update = retrieved.last_update, 
                        status_changed_at = retrieved.status_changed_at,
                        last_success_at = retrieved.last_success_at,
                        last_failure_at = retrieved.last_failure_at,
                        records_inserted = retrieved.records_inserted, 
                        records_rejected = retrieved.records_rejected
                    )
            end_time = time.perf_counter()
            self.ctx.logger.info(
                msg=f"SET_TABLE_CONTROL_STATUS_TO_{action}_END",
                extra={
                    "step": step,
                    "table": fq_table_name,
                    "duration_s": round(end_time - start_time, 2)
                }
            )
            return updated_record
        except Exception:
            self.ctx.logger.exception(
                msg=f"SET_TABLE_CONTROL_STATUS_TO_{action}_EXCEPTION",
                extra={
                    "step": step,
                    "table": fq_table_name
                }
            )
            raise