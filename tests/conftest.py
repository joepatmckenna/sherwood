from calendar import timegm
from contextlib import asynccontextmanager
import datetime
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import jose.jwt
import os
import pytest
from sherwood.auth import _JWT_ALGORITHM, _JWT_ISSUER, JWT_SECRET_KEY_ENV_VAR_NAME
from sherwood.db import get_db, Session
from sherwood.main import create_app
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv(".env.dev", override=True)
engine = create_engine(
    URL.create(
        drivername="sqlite",
        database=":memory:",
    ),
    # URL.create(
    #     drivername="postgresql",
    #     username="joe",
    #     host="localhost",
    #     port=5432,
    #     database="db",
    # )
    connect_args={"check_same_thread": False},
)
Session.configure(bind=engine)


@pytest.fixture(scope="function")
def db():
    BaseModel.metadata.create_all(engine)
    yield from get_db()
    BaseModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client():
    @asynccontextmanager
    async def lifespan(_):
        BaseModel.metadata.create_all(engine)
        yield
        BaseModel.metadata.drop_all(engine)

    app = create_app(lifespan=lifespan)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_get_price(mocker):
    mocker.patch.object(
        MarketDataProvider,
        "get_price",
        side_effect=lambda symbol: {"AAA": 1, "BBB": 2}[symbol],
    )


@pytest.fixture
def valid_email(scope="session"):
    return "user@web.com"


@pytest.fixture
def valid_emails(scope="session"):
    return [f"user{i}@web.com" for i in range(10)]


@pytest.fixture
def valid_password(scope="session"):
    return "Abcd@1234"


@pytest.fixture(scope="session")
def fake_access_token():
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    expiration = issued_at + datetime.timedelta(hours=1)
    return jose.jwt.encode(
        claims={
            "iss": _JWT_ISSUER,
            "sub": "0",
            "exp": timegm(expiration.utctimetuple()),
            "iat": timegm(issued_at.utctimetuple()),
        },
        key=os.environ[JWT_SECRET_KEY_ENV_VAR_NAME],
        algorithm=_JWT_ALGORITHM,
    )
