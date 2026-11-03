import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.audit_log import AuditLog
from app.services.audit_service import get_audit_logs, log_audit

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# TC-Audit-01.1
def test_log_audit_stores_fields(db):
    audit = log_audit(
        db,
        user_id=1,
        action="create_supplier",
        entity="supplier",
        entity_id=42,
    )

    assert audit.id is not None
    assert audit.user_id == 1
    assert audit.action == "create_supplier"
    assert audit.entity == "supplier"
    assert audit.entity_id == 42
    assert audit.timestamp is not None


# TC-Audit-01.2
def test_invalid_inputs_rejected(db):
    with pytest.raises(Exception):
        log_audit(db, user_id=0, action="x", entity="y", entity_id=1)

    with pytest.raises(Exception):
        log_audit(db, user_id=1, action="", entity="y", entity_id=1)

    with pytest.raises(Exception):
        log_audit(db, user_id=1, action="x", entity="", entity_id=1)

    with pytest.raises(Exception):
        log_audit(db, user_id=1, action="x", entity="y", entity_id=0)


# TC-Audit-01.3
def test_filters_by_user_entity_and_action(db):
    log_audit(db, user_id=1, action="create_supplier", entity="supplier", entity_id=1)
    log_audit(db, user_id=2, action="create_supplier", entity="supplier", entity_id=2)
    log_audit(db, user_id=1, action="deduct_stock", entity="product", entity_id=1)

    by_user_1 = get_audit_logs(db, user_id=1)
    assert len(by_user_1) == 2
    assert all(row.user_id == 1 for row in by_user_1)

    by_entity = get_audit_logs(db, entity="supplier")
    assert len(by_entity) == 2

    by_action = get_audit_logs(db, action="create_supplier")
    assert len(by_action) == 2


# TC-Audit-01.4
def test_newest_first(db):
    log_audit(db, user_id=1, action="a", entity="e", entity_id=1)
    log_audit(db, user_id=1, action="b", entity="e", entity_id=2)

    logs = get_audit_logs(db)

    assert len(logs) == 2
    assert logs[0].timestamp >= logs[1].timestamp
