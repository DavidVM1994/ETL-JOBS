import os
from dataclasses import dataclass
from common.database.env import require_key

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
        
        def req(key: str) -> str:
            return require_key(f"{prefix}_{key}")
        
        def opt(key: str, default: str | None = None) -> str | None:
            return os.getenv(
                key=f"{prefix}_{key}",
                default=default
            )
        return cls(
            host=req(key="HOST"),
            port=int(req(key="PORT")),
            dbname=req(key="DATABASE"),
            username=req(key="USERNAME"),
            password=req(key="PASSWORD"),
            schema=opt(key="SCHEMA"),
            driver=opt(key="DRIVER"),
            application_name=opt(key="APPLICATION"),
            login_timeout=int(opt(key="LOGIN_TIME", default="10")),
            connection_timeout=int(opt(key="CONNECTION_TIME", default="10"))
        )