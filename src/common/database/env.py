import os
from pathlib import Path
import dotenv

_loaded=False

def load_env(path: Path)->None:
    global _loaded

    if not path.exists() or not path.is_file():
        raise FileNotFoundError("file does not exist or is not a file")
    if not _loaded:
        dotenv.load_dotenv(dotenv_path=path)
        _loaded = True

def require_key(key:str)->str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"required environment variable {key} not set")
    return value