from typing import Protocol
import polars as pl

class PolarsReader(Protocol):
    def read(self)-> pl.DataFrame:
        ...