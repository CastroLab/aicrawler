import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: register all models

from fastapi.testclient import TestClient


@pytest.fixture
def db_engine():
    # Use StaticPool to keep the same in-memory db across connections
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title, summary, content='articles', content_rowid='id'
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, summary)
                VALUES (new.id, new.title, COALESCE(new.summary, ''));
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, summary)
                VALUES ('delete', old.id, old.title, COALESCE(old.summary, ''));
                INSERT INTO articles_fts(rowid, title, summary)
                VALUES (new.id, new.title, COALESCE(new.summary, ''));
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, summary)
                VALUES ('delete', old.id, old.title, COALESCE(old.summary, ''));
            END
        """))
        conn.commit()

    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    Session = sessionmaker(bind=db_engine)

    def _override():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(client, db_session):
    """A client that is logged in as admin."""
    from passlib.hash import bcrypt
    from app.models.user import User

    user = User(
        username="testadmin",
        password_hash=bcrypt.hash("testpass"),
        display_name="Test Admin",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()

    client.post("/login", data={"username": "testadmin", "password": "testpass"})
    return client
