import sys
import os
import json
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../server'))

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./test_hitl.db"
os.environ["MASTER_ENCRYPTION_KEY"] = "g6900R-8-M_1_s_V_P_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S_S="

from main import app
from database import Base, async_engine, AsyncSessionLocal
from models import AIConfig
from routers.auth import get_current_user

@pytest.fixture(autouse=True)
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_hitl_approval_pipeline():
    """
    Full Pipeline Test:
    1. Incoming message -> triggers pending status (mocked low confidence)
    2. Admin approved -> status changes to 'sent'
    """
    
    # 1. Seed Active Config
    async with AsyncSessionLocal() as db:
        config = AIConfig(
            id=1, 
            is_active=True, 
            whatsapp_driver="mock",
            auto_respond_threshold=90,
            review_threshold=60,
            auto_send_delay=0
        )
        db.add(config)
        await db.commit()

    # 2. Mock dependencies
    mock_user = MagicMock(id=1, username="admin", role="admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        try:
            with patch("services.ai_agent.AIAgent.generate_response", new_callable=AsyncMock) as mock_gen, \
                 patch("routers.websocket.ConnectionManager.broadcast", new_callable=AsyncMock) as mock_ws, \
                 patch("services.whatsapp_service.WhatsAppService.get_driver") as mock_driver_factory:
                
                mock_gen.return_value = {
                    "content": "This is a suggestion that needs review.",
                    "confidence": 70,
                    "metadata": {
                        "intent": "Sales",
                        "classification": "safe",
                        "status_suggestion": "pending"
                    }
                }
                
                mock_driver = MagicMock()
                mock_driver.send_message = AsyncMock(return_value="wamid.test12345")
                mock_driver_factory.return_value = mock_driver

                # 3. Incoming message
                payload = {
                    "sender": "50688888888",
                    "message": "Hola, necesito informacion de precios",
                    "id": "external_123"
                }
                response = await ac.post("/whatsapp/webhook", json=payload)
                assert response.status_code == 200
                
                # 4. Check conversations
                response = await ac.get("/conversations/")
                assert response.status_code == 200
                convs = response.json()
                assert len(convs) > 0
                conv_id = convs[0]["id"]
                
                # 5. Check messages
                response = await ac.get(f"/conversations/{conv_id}/messages")
                msgs = response.json()
                agent_msg = next((m for m in msgs if m["sender"] == "agent"), None)
                assert agent_msg is not None
                assert agent_msg["status"] == "pending"
                msg_id = agent_msg["id"]
                
                # 6. Approve
                response = await ac.post(f"/conversations/messages/{msg_id}/approve")
                assert response.status_code == 200
                
                # 7. Verify final
                response = await ac.get(f"/conversations/{conv_id}/messages")
                msgs = response.json()
                approved_msg = next((m for m in msgs if m["id"] == msg_id), None)
                assert approved_msg["status"] == "sent"
                mock_driver.send_message.assert_called_once()
                
        finally:
            app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/metrics/")
        assert response.status_code == 200
        assert "ai_requests_total" in response.text
