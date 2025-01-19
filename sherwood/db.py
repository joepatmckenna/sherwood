from fastapi import Depends
from sherwood.errors import InternalServerError
from sqlalchemy.orm import sessionmaker, Session as SqlAlchemyOrmSession
from typing import Annotated

POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME = "POSTGRESQL_DATABASE_PASSWORD"

Session = sessionmaker(autocommit=False, autoflush=False)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def maybe_commit(db: SqlAlchemyOrmSession, error_message: str):
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise InternalServerError(f"{error_message} Error: {exc}") from exc


Database = Annotated[SqlAlchemyOrmSession, Depends(get_db)]
