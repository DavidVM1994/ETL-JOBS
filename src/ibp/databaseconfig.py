from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    dbschema: str
    username: str
    password: str