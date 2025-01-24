from functools import wraps
from sherwood.errors import InternalServerError, SherwoodError


class HandleErrors:
    def __init__(self, expected_error_types: tuple[SherwoodError]):
        self._expected_error_types = expected_error_types

    def __call__(self, f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except self._expected_error_types:
                raise
            except Exception as exc:
                raise InternalServerError(
                    f"Unexpected error (func={f}, args={args}, kwargs={kwargs}, error={repr(exc)})"
                ) from exc

        return wrapper
