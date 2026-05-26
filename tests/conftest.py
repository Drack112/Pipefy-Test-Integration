import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db

_ADMIN_URL = settings.database_url
_TEST_DB_NAME = "test_appdb"
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    _ADMIN_URL.rsplit("/", 1)[0] + f"/{_TEST_DB_NAME}",
)


def _ddl(statement: str) -> None:
    engine = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(statement))
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_database():
    _ddl(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{_TEST_DB_NAME}' AND pid <> pg_backend_pid()"
    )
    _ddl(f"DROP DATABASE IF EXISTS {_TEST_DB_NAME}")
    _ddl(f"CREATE DATABASE {_TEST_DB_NAME}")
    yield
    _ddl(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{_TEST_DB_NAME}' AND pid <> pg_backend_pid()"
    )
    _ddl(f"DROP DATABASE IF EXISTS {_TEST_DB_NAME}")


@pytest.fixture(scope="session")
def test_engine(test_database):
    engine = create_engine(_TEST_DATABASE_URL)
    import app.db.models.client  # noqa: F401
    import app.db.models.webhook_event  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def clean_db(test_engine):
    yield
    table_names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    if table_names:
        with test_engine.connect() as conn:
            conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
            conn.commit()


@pytest.fixture
def client(db_factory):
    from main import app

    def _get_test_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
