import os
from pathlib import Path
import dotenv

from common.databaseconfig import DatabaseConfig
from common.logging_config import Context, LoggingSetup

class Configs:
    source_database: DatabaseConfig
    target_database: DatabaseConfig
    ctx: Context
    def __init__(
            self,
            source_database: DatabaseConfig,
            target_database: DatabaseConfig,
            ctx: Context
    )->None:
        self.source_database = source_database
        self.target_database = target_database
        self.ctx = ctx

    @staticmethod
    def load_config(env_file_path: Path, tracking_id: str, object_id: str, business_id: str)->Configs:

        if not env_file_path.exists() or (not env_file_path.is_file()):
            raise RuntimeError(
                f"File {env_file_path} does not exist or is not a file"
            )

        if not dotenv.load_dotenv(env_file_path):
            raise RuntimeError(
                "Failed to load .env file."
            )

        required = [
            "SOURCE_HOST", "SOURCE_PORT", "SOURCE_DATABASE", "SOURCE_USERNAME", "SOURCE_PASSWORD",
            "TARGET_HOST", "TARGET_PORT", "TARGET_DATABASE", "TARGET_USERNAME", "TARGET_PASSWORD",
            "LOG_FILE_PATH", "LOGGER_NAME", "LOG_LEVEL", "CONSOLE_STRING_FORMAT", "CONSOLE_DATE_FORMAT",
            "WRITE_MODE", "ENCODING"
        ]

        missing = [
            k for k in required if not os.getenv(k)
        ]
        if missing:
            raise ValueError(
                "missing required environment variables: {}".format(missing)
            )

        source_config = DatabaseConfig(
            host=os.getenv("SOURCE_HOST"),
            port=int(os.getenv("SOURCE_PORT")),
            dbname=os.getenv("SOURCE_DATABASE"),
            username=os.getenv("SOURCE_USERNAME"),
            password=os.getenv("SOURCE_PASSWORD")
        )

        target_config = DatabaseConfig(
            host=os.getenv("TARGET_HOST"),
            port=int(os.getenv("TARGET_PORT")),
            dbname=os.getenv("TARGET_DATABASE"),
            username=os.getenv("TARGET_USERNAME"),
            password=os.getenv("TARGET_PASSWORD")
        )

        logger = LoggingSetup.setup_logging(
            file_path=os.getenv("LOG_FILE_PATH"),
            logger_name=os.getenv("LOG_FILE_PATH"),
            logger_level=int(os.getenv("LOG_LEVEL")),
            console_string_format=os.getenv("CONSOLE_STRING_FORMAT"),
            console_date_format=os.getenv("CONSOLE_DATE_FORMAT"),
            encoding=os.getenv("ENCODING")
        )

        ctx = Context.configure_context(
            tracking_id=tracking_id,
            object_id=object_id,
            business_id=business_id,logger=logger
        )

        configs = Configs(
            source_database=source_config,
            target_database=target_config,
            ctx=ctx
        )
        return configs