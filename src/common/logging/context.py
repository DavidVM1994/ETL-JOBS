import contextvars
from contextlib import contextmanager
from typing import Any, Iterator

log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "log_context",
    default={}
)

@contextmanager
def bind_context_scope(**fields: Any) -> Iterator[None]:
    current = log_context.get().copy()
    current.update(fields)
    token = log_context.set(current)
    try:
        yield
    finally:
        log_context.reset(token)

def bind_log_context(**fields: Any) -> None:
    current = log_context.get().copy()
    current.update(fields)
    log_context.set(current)

def clear_log_context():
    log_context.set({})