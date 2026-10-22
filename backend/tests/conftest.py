from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: object) -> Iterator[TestClient]:
    database_path = tmp_path / "threatlens-test.db"  # type: ignore[operator]
    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-that-is-long-enough-for-tests",
        database_url=f"sqlite+aiosqlite:///{database_path}",
        auto_create_schema=True,
        seed_source_catalog=True,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
