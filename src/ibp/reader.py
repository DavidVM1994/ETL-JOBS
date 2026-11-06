import os
from logging import Logger
from pathlib import Path
from time import perf_counter
from urllib.parse import quote

import polars
from psutil import Process
from datetime import datetime

from common.database.config import DatabaseConfig, Table


def read_from_database_to_csv(
        src_database_config: DatabaseConfig,
        src_table: Table,
        dir_path: Path,
        logger: Logger,
        step: str,
        partition_num: int = 8,
)->Path:
    logger.info(
        msg="EXTRACT_START",
        extra={
            "step": step
        }
    )
    process = Process(pid=os.getpid())
    start_time = perf_counter()
    start_rss = process.memory_info().rss
    gen_time = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    try:
        if not dir_path.exists() or not dir_path.is_dir():
            raise RuntimeError(
                f"Path does not exist or it's not a directory: {dir_path}"
            )

        uri = f"redshift://{src_database_config.username}:{quote(src_database_config.password, safe="")}@{src_database_config.host}:{src_database_config.port}/{src_database_config.dbname}"
        sql = f"SELECT * FROM {src_table.table_schema}.{src_table.table_name}"
        logger.info(
            msg="READ_FROM_SOURCE_TABLE_START",
            extra={}
        )
        df = polars.read_database_uri(
            uri=uri,
            query=sql,
            partition_num=partition_num
        )
        records_extracted = len(df)
        logger.info(
            msg="READ_FROM_SOURCE_TABLE_END",
            extra={
                "step": step,
                "records_extracted": records_extracted,
                "duration_s": round(perf_counter() - start_time, 2),
                "rss_delta": round(process.memory_info().rss - start_rss / 1024 ** 2, 2)
            }
        )

        logger.info(
            msg="WRITE_TO_CSV_START",
            extra={
                "step": step
            }
        )
        start_time = perf_counter()
        file_path = dir_path / f"export_{gen_time}.csv"
        file = df.write_csv(
            file=file_path
        )
        duration = round(perf_counter() - start_time,2)
        logger.info(
            msg="WRITE_TO_CSV_END",
            extra={
                "step": step,
                "duration_s": duration
            }
        )

        return file_path

    except Exception:
        logger.exception(
            msg="EXTRACT_EXCEPTION",
            extra={
                "step": step
            }
        )
        raise