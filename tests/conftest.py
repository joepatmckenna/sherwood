from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
import os
import pytest
import secrets
from sherwood.auth import JWT_SECRET_KEY_ENV_VAR_NAME
from sherwood.db import get_db, DB_PWD_ENV_VAR_NAME
from sherwood.main import create_app
from sherwood.market_data_provider import MarketDataProvider
from sherwood.models import BaseModel
from sqlalchemy import create_engine
import sqlalchemy.orm


@pytest.fixture(scope="session", autouse=True)
def set_environment_variables():
    os.environ[JWT_SECRET_KEY_ENV_VAR_NAME] = secrets.token_hex(32)
    os.environ[DB_PWD_ENV_VAR_NAME] = "password"


@pytest.fixture(autouse=True)
def mock_get_price(mocker):
    def _mock_get_price(symbol):
        return {
            "AAA": 1,
            "BBB": 2,
        }[symbol]

    mocker.patch.object(
        MarketDataProvider,
        "get_price",
        side_effect=_mock_get_price,
    )


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)

TestSession = sqlalchemy.orm.sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest.fixture
def valid_email(scope="session"):
    return "user@web.com"


@pytest.fixture
def valid_password(scope="session"):
    return "Abcd@1234"


def get_test_db():
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(scope="function")
def db():
    BaseModel.metadata.create_all(bind=engine)
    yield from get_test_db()
    BaseModel.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    @asynccontextmanager
    async def lifespan(_):
        BaseModel.metadata.create_all(engine)
        yield
        BaseModel.metadata.drop_all(engine)

    app = create_app(lifespan=lifespan)
    app.dependency_overrides[get_db] = lambda: (yield from get_test_db())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
