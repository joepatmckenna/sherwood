from sqlalchemy.orm import sessionmaker

POSTGRESQL_DATABASE_PASSWORD_ENV_VAR_NAME = "POSTGRESQL_DATABASE_PASSWORD"

Session = sessionmaker(autocommit=False, autoflush=False)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
