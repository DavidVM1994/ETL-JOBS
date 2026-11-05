import os
from dataclasses import dataclass
from common.database.env import require_key


def _opt(key: str, prefix: str | None = None, default: str | None = None) -> str | None:
    return os.getenv(
        key=f"{prefix}_{key}",
        default=default
    )


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    username: str
    password: str
    schema: str | None = None
    driver: str | None = None
    application_name: str | None = None
    login_timeout: int = 10
    connection_timeout: int = 10

    @classmethod
    def from_env(cls, prefix: str | None = None) -> DatabaseConfig:
        return cls(
            host=require_key(key="HOST", prefix=prefix),
            port=int(require_key(key="PORT", prefix=prefix)),
            dbname=require_key(key="DATABASE", prefix=prefix),
            username=require_key(key="USERNAME", prefix=prefix),
            password=require_key(key="PASSWORD", prefix=prefix),
            schema=_opt(key="SCHEMA", prefix=prefix),
            driver=_opt(key="DRIVER", prefix=prefix),
            application_name=_opt(key="APPLICATION"),
            login_timeout=int(_opt(key="LOGIN_TIME", default="10")),
            connection_timeout=int(_opt(key="CONNECTION_TIME", default="10"))
        )


@dataclass(frozen=True)
class Table:
    table_schema: str
    table_name: str

    @classmethod
    def from_env(cls, prefix: str | None = None) -> Table:
        return cls(
            table_schema=require_key(key="TABLE_SCHEMA", prefix=prefix),
            table_name=require_key(key="TABLE_NAME", prefix=prefix)
        )