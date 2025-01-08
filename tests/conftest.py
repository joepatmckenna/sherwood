from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import os
import pytest
from sherwood.db import get_db, Session, POSTGRESQL_DATABASE_URL_ENV_VAR_NAME
from sherwood.main import create_app
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import BaseModel
from sqlalchemy import create_engine

load_dotenv(".env.dev")

engine = create_engine(
    os.environ[POSTGRESQL_DATABASE_URL_ENV_VAR_NAME],
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
def valid_password(scope="session"):
    return "Abcd@1234"
