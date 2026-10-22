import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.session as session_module
import app.db.init_db as init_db_module
from app.db.session import Base, get_db, SessionLocal, engine
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(autouse=True, scope="function")
def isolate_database_for_tests():
    """
    Autouse fixture that runs for every test.
    Ensures that every test runs against an isolated in-memory SQLite database
    and that the real on-disk saferail.db is NEVER touched or modified.
    """
    # 1. Create in-memory SQLite database with StaticPool
    test_engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # 2. Rebind the existing sessionmaker in place
    orig_engine = session_module.engine
    session_module.engine = test_engine
    init_db_module.engine = test_engine
    SessionLocal.configure(bind=test_engine)

    # 3. Create schema and initial seed data in the in-memory database
    Base.metadata.create_all(bind=test_engine)
    init_db_module.init_db()

    # 4. Override FastAPI dependency
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    # 5. Clean up and restore
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    SessionLocal.configure(bind=orig_engine)
    session_module.engine = orig_engine
    init_db_module.engine = orig_engine
