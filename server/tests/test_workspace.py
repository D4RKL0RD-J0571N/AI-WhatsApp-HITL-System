
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Adjust imports to match PYTHONPATH=./server (set in CI)
import sys
import os
# We don't need sys.path hack if PYTHONPATH is set, but helpful for local:
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from main import app
from database import Base, get_async_db
from routers.auth import get_admin_user
from models import AIConfig, User

# Setup In-Memory Async DB for Testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def override_get_async_db():
    async with TestingSessionLocal() as session:
        yield session

# Mock Admin User
def override_get_admin_user():
    return User(id=1, username="admin", role="admin", is_active=True)

app.dependency_overrides[get_async_db] = override_get_async_db
app.dependency_overrides[get_admin_user] = override_get_admin_user

client = TestClient(app)

# Helper to Initialize DB with Seed Data
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        # Create a default active config
        config = AIConfig(
            business_name="Test Business",
            business_description="A test business",
            tone="Professional",
            rules_json="[]",
            forbidden_topics_json="[]",
            intent_rules_json="[]",
            suggestions_json="[]",
            workspace_config="{}",
            is_active=True,
            # Defaults for non-nullable fields if any not covered by defaultModel values
            auto_respond_threshold=90,
            review_threshold=50
            # Secrets might be nullable, so this should be enough
        )
        session.add(config)
        await session.commit()

def test_save_and_retrieve_workspace_config():
    # 1. Initialize DB (Blocking wait)
    asyncio.run(init_test_db())

    # 2. Save Config
    payload = {
        "config": '{"layout_mode": "grid", "open_conversations": [1, 2, 3]}'
    }
    response = client.post("/admin/workspace", json=payload)
    assert response.status_code == 200, f"Response: {response.text}"
    assert response.json()["status"] == "success"

    # 3. Retrieve Config (via GET /admin/config)
    response = client.get("/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert "workspace_config" in data
    assert data["workspace_config"] == payload["config"]
