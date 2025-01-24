from functools import wraps
import json
import logging
from pydantic import BaseModel
from sherwood.errors import *
from sherwood.models import has_expired, upsert_blob, Blob
from sqlalchemy.orm import Session


class Cache:
    """Decorator for caching request/response pairs in the db.

    Example usage:

      @api_router.post("/fake")
      @cache(lifetime_seconds=10)
      async def api_fake(request: FakeRequest, db: Database) -> FakeResponse:
          return FakeResponse(...)

      where:
       - FakeRequest / FakeResponse are descendents of BaseModel
       - db is a sqlalchemy.orm.Session
    """

    def __init__(self, lifetime_seconds: int):
        self._lifetime_seconds = lifetime_seconds

    def __call__(self, f):
        @wraps(f)
        async def wrapper(*args, **kwargs) -> BaseModel:
            request = kwargs.get("request")
            if request is None:
                raise InternalServerError(f"missing request kwarg.")
            request_type = type(request)
            if not BaseModel in request_type.__mro__:
                raise InternalServerError(f"BaseModel not in request mro: {request}.")
            if not isinstance(db := kwargs.get("db"), Session):
                raise InternalServerError(f"db is not a sqlalchemy.orm.Session: {db}.")

            key = f"{request_type}({request.model_dump_json()})"

            blob = db.get(Blob, key)
            if blob is None or has_expired(blob, self._lifetime_seconds):
                result = await f(*args, **kwargs)
                value = result.model_dump_json()
                blob = upsert_blob(db, key, value)

            return_type = f.__annotations__.get("return")
            if isinstance(return_type, type) and BaseModel in return_type.__mro__:
                return return_type.model_validate_json(blob.value)

            logging.info("cache not validating response type")
            return json.loads(blob.value)

        return wrapper
