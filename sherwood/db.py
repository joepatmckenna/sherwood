import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DB_PWD_ENV_VAR_NAME = "DB_PWD"

engine = create_engine(
    f"postgresql://postgres:{os.getenv(DB_PWD_ENV_VAR_NAME)}@localhost/db"
)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
