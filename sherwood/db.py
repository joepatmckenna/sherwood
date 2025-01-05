from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:passwordd@localhost/db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
