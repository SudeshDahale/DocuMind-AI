"""
Retry + fallback utilities used across all services.
"""

import time
import functools
from typing import Callable, Type, Tuple, Any
from core.logger import get_logger

log = get_logger("errors")


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    fallback: Any = None,
    reraise: bool = True,
):
    """
    Decorator factory — retries a function with exponential backoff.

    Args:
        max_attempts : total attempts (1 = no retry)
        delay        : initial wait in seconds
        backoff      : multiplier applied after each failure
        exceptions   : which exception types trigger a retry
        fallback     : value to return if all attempts fail (only when reraise=False)
        reraise      : if True, raise the final exception; if False, return fallback
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    log.warning(
                        f"{fn.__name__} failed (attempt {attempt}/{max_attempts})",
                        extra={
                            "fn": fn.__name__,
                            "attempt": attempt,
                            "error": str(exc),
                            "retry_in": wait if attempt < max_attempts else None,
                        },
                    )
                    if attempt < max_attempts:
                        time.sleep(wait)
                        wait *= backoff
            if reraise:
                raise last_exc
            log.error(
                f"{fn.__name__} exhausted all retries — returning fallback",
                extra={"fn": fn.__name__, "fallback": str(fallback)},
            )
            return fallback
        return wrapper
    return decorator