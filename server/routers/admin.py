from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_db
from models import AIConfig, AIDataset, AIConfigSnapshot, Message, SecurityAudit, User, AuditLog
from pydantic import BaseModel
from typing import List, Optional
import json
from logger import setup_logger
from services.ai_agent import AIAgent
from routers.auth import get_admin_user
import os
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo # Fallback for older python if needed, but 3.9+ has it
from services.encryption import encrypt_string, decrypt_string
from services.knowledge_service import KnowledgeService
from fastapi import File, UploadFile

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = setup_logger("admin")
ai_agent = AIAgent()

from typing import List, Optional

class AIConfigRequest(BaseModel):
    business_name: str
    business_description: str
    tone: str
    rules: List[str]
    auto_respond_threshold: int
    review_threshold: int
    forbidden_topics: List[str]
    language_code: str = "es-CR"
    translate_messages: bool = False
    identity_prompt: Optional[str] = None
    grounding_template: Optional[str] = None
    intent_rules: List[dict] = []
    fallback_message: str = "I am currently having trouble processing your request."
    preferred_model: str = "gpt-4-turbo"
    logo_url: Optional[str] = None
    primary_color: str = os.getenv("DEFAULT_PRIMARY_COLOR", "#2563eb")
    ui_density: str = "comfortable"
    # Secrets
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = os.getenv("OPENAI_API_BASE", "http://localhost:1234/v1")
    whatsapp_api_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_driver: str = "mock"
    timezone: str = "UTC"
    workspace_config: str = "{}"
    suggestions_json: List[str] = []

@router.get("/config")
async def get_ai_config(db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="AI Configuration not found. Please create one.")
    
    return {
        "business_name": config.business_name,
        "business_description": config.business_description,
        "tone": config.tone,
        "rules": json.loads(config.rules_json),
        "auto_respond_threshold": config.auto_respond_threshold,
        "review_threshold": config.review_threshold,
        "forbidden_topics": json.loads(config.forbidden_topics_json),
        "language_code": config.language_code,
        "translate_messages": config.translate_messages,
        "identity_prompt": config.identity_prompt,
        "grounding_template": config.grounding_template,
        "intent_rules": json.loads(config.intent_rules_json),
        "fallback_message": config.fallback_message,
        "preferred_model": getattr(config, 'preferred_model', 'gpt-4-turbo'),
        "logo_url": getattr(config, 'logo_url', None),
        "primary_color": getattr(config, 'primary_color', os.getenv("DEFAULT_PRIMARY_COLOR", "#2563eb")),
        "ui_density": getattr(config, 'ui_density', 'comfortable'),
        # Secrets (Masked for security in real app, but explicit here for admin)
        "openai_api_base": getattr(config, 'openai_api_base', os.getenv("OPENAI_API_BASE", "http://localhost:1234/v1")),
        "openai_api_key": decrypt_string(getattr(config, 'openai_api_key', None)) if getattr(config, 'openai_api_key', None) else None,
        "whatsapp_api_token": decrypt_string(getattr(config, 'whatsapp_api_token', None)) if getattr(config, 'whatsapp_api_token', None) else None,
        "timezone": getattr(config, 'timezone', 'UTC'),
        "workspace_config": getattr(config, 'workspace_config', '{}'),
        "suggestions_json": json.loads(config.suggestions_json or "[]"),
        "whatsapp_phone_id": getattr(config, 'whatsapp_phone_id', None),
        "whatsapp_driver": getattr(config, 'whatsapp_driver', 'mock')
    }

@router.post("/config")
async def update_ai_config(req: AIConfigRequest, db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    if not config:
        config = AIConfig()
        db.add(config)
    
    config.business_name = req.business_name
    config.business_description = req.business_description
    config.tone = req.tone
    config.rules_json = json.dumps(req.rules)
    config.auto_respond_threshold = req.auto_respond_threshold
    config.review_threshold = req.review_threshold
    config.forbidden_topics_json = json.dumps(req.forbidden_topics)
    config.language_code = req.language_code
    config.translate_messages = req.translate_messages
    config.identity_prompt = req.identity_prompt
    config.grounding_template = req.grounding_template
    config.intent_rules_json = json.dumps(req.intent_rules)
    config.fallback_message = req.fallback_message
    config.preferred_model = req.preferred_model
    config.logo_url = req.logo_url
    config.primary_color = req.primary_color
    config.ui_density = req.ui_density
    
    # Secrets Update (Only if provided, to avoid clearing on empty)
    if req.openai_api_key:
        config.openai_api_key = encrypt_string(req.openai_api_key)
    if req.openai_api_base:
        config.openai_api_base = req.openai_api_base
    if req.whatsapp_api_token:
        config.whatsapp_api_token = encrypt_string(req.whatsapp_api_token)
    if req.whatsapp_verify_token:
        config.whatsapp_verify_token = encrypt_string(req.whatsapp_verify_token)
        
    config.timezone = req.timezone
    config.workspace_config = req.workspace_config
    config.suggestions_json = json.dumps(req.suggestions_json)
    config.whatsapp_phone_id = req.whatsapp_phone_id
    config.whatsapp_driver = req.whatsapp_driver
    
    await db.commit()
    await db.refresh(config)
    
    # --- AUTOMATIC SNAPSHOT ---
    snapshot = AIConfigSnapshot(
        config_id=config.id,
        business_name=config.business_name,
        business_description=config.business_description,
        tone=config.tone,
        rules_json=config.rules_json,
        auto_respond_threshold=config.auto_respond_threshold,
        review_threshold=config.review_threshold,
        auto_send_delay=config.auto_send_delay or 30,
        keywords_json=config.keywords_json or "[]",
        forbidden_topics_json=config.forbidden_topics_json,
        language_code=config.language_code,
        translate_messages=config.translate_messages,
        identity_prompt=config.identity_prompt,
        grounding_template=config.grounding_template,
        intent_rules_json=config.intent_rules_json,
        fallback_message=config.fallback_message,
        preferred_model=config.preferred_model,
        whatsapp_driver=config.whatsapp_driver,
        whatsapp_phone_id=config.whatsapp_phone_id,
        logo_url=config.logo_url,
        primary_color=config.primary_color,
        version_name=f"Standard v{config.updated_at.strftime('%m%d.%H%M')}",
        version_label=f"Auto-saved version {config.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    db.add(snapshot)
    await db.commit()
    # ---------------------------

    # --- AUDIT LOG ---
    audit = AuditLog(
        user_id=admin.id,
        action="UPDATE_CONFIG",
        resource="AIConfig",
        details=f"Updated business configuration: {req.business_name}"
    )
    db.add(audit)
    await db.commit()
    # -----------------

    logger.info("AI Configuration updated and snapshot created")
    return {"status": "success", "message": "Configuration updated and snapshot created"}

@router.get("/snapshots")
async def list_snapshots(db: AsyncSession = Depends(get_async_db)):
    """List all saved configuration snapshots."""
    result = await db.execute(select(AIConfigSnapshot).order_by(AIConfigSnapshot.created_at.desc()).limit(20))
    snapshots = result.scalars().all()
    return snapshots

@router.post("/snapshots/{snapshot_id}/rollback")
async def rollback_to_snapshot(snapshot_id: int, db: AsyncSession = Depends(get_async_db)):
    """Rollback the active configuration to a specific snapshot."""
    result = await db.execute(select(AIConfigSnapshot).filter(AIConfigSnapshot.id == snapshot_id))
    snapshot = result.scalars().first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    if not config:
        config = AIConfig()
        db.add(config)
    
    # Restore all fields from snapshot
    config.business_name = snapshot.business_name
    config.business_description = snapshot.business_description
    config.tone = snapshot.tone
    config.rules_json = snapshot.rules_json
    config.auto_respond_threshold = snapshot.auto_respond_threshold
    config.review_threshold = snapshot.review_threshold
    config.auto_send_delay = snapshot.auto_send_delay
    config.keywords_json = snapshot.keywords_json
    config.forbidden_topics_json = snapshot.forbidden_topics_json
    config.language_code = snapshot.language_code
    config.translate_messages = snapshot.translate_messages
    config.identity_prompt = snapshot.identity_prompt
    config.grounding_template = snapshot.grounding_template
    config.intent_rules_json = snapshot.intent_rules_json
    config.fallback_message = snapshot.fallback_message
    config.preferred_model = snapshot.preferred_model
    config.logo_url = snapshot.logo_url
    config.primary_color = snapshot.primary_color
    
    await db.commit()
    logger.info(f"AI Configuration rolled back to snapshot {snapshot_id}")
    return {"status": "success", "message": f"Rolled back to {snapshot.version_name or snapshot.version_label or snapshot.created_at}"}

@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: int, db: AsyncSession = Depends(get_async_db)):
    """Delete a configuration snapshot if it's not locked."""
    result = await db.execute(select(AIConfigSnapshot).filter(AIConfigSnapshot.id == snapshot_id))
    snapshot = result.scalars().first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    if snapshot.is_locked:
        raise HTTPException(status_code=400, detail="Cannot delete a locked snapshot")
    
    await db.delete(snapshot)
    await db.commit()
    logger.info(f"Snapshot {snapshot_id} deleted")
    return {"status": "success", "message": "Snapshot deleted"}

class SnapshotRenameRequest(BaseModel):
    name: str

@router.put("/snapshots/{snapshot_id}/name")
async def rename_snapshot(snapshot_id: int, req: SnapshotRenameRequest, db: AsyncSession = Depends(get_async_db)):
    """Rename a configuration snapshot."""
    result = await db.execute(select(AIConfigSnapshot).filter(AIConfigSnapshot.id == snapshot_id))
    snapshot = result.scalars().first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    snapshot.version_name = req.name
    await db.commit()
    return {"status": "success", "message": "Snapshot renamed", "new_name": req.name}

@router.post("/snapshots/{snapshot_id}/toggle-lock")
async def toggle_snapshot_lock(snapshot_id: int, db: AsyncSession = Depends(get_async_db)):
    """Toggle the lock status of a snapshot to prevent accidental deletion."""
    result = await db.execute(select(AIConfigSnapshot).filter(AIConfigSnapshot.id == snapshot_id))
    snapshot = result.scalars().first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    snapshot.is_locked = not getattr(snapshot, "is_locked", False)
    await db.commit()
    return {"status": "success", "is_locked": snapshot.is_locked}

class WorkspaceConfigRequest(BaseModel):
    config: str

@router.post("/workspace")
async def save_workspace_config(req: WorkspaceConfigRequest, db: AsyncSession = Depends(get_async_db)):
    """Save persistent UI layout preferences."""
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    config.workspace_config = req.config
    await db.commit()
    return {"status": "success"}

class AITestRequest(BaseModel):
    message: str

@router.post("/test")
async def test_ai_response(req: AITestRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Test how the AI responds to a message given the current global config.
    """
    logger.info(f"Admin running AI Sandbox test: {req.message[:50]}...")
    
    # We use a dummy client_id for testing
    result = await ai_agent.generate_response("admin_test_user", req.message, db=db)
    
    return result

class AIDatasetRequest(BaseModel):
    name: str
    data_type: str
    content: str

@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AIDataset))
    datasets = result.scalars().all()
    return datasets

@router.post("/datasets")
async def create_dataset(req: AIDatasetRequest, db: AsyncSession = Depends(get_async_db)):
    logger.info(f"Adding new dataset: {req.name}")
    new_ds = AIDataset(
        name=req.name,
        data_type=req.data_type,
        content=req.content
    )
    db.add(new_ds)
    await db.commit()
    await db.refresh(new_ds)
    return new_ds

@router.post("/datasets/{ds_id}/toggle")
async def toggle_dataset(ds_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AIDataset).filter(AIDataset.id == ds_id))
    ds = result.scalars().first()
    if ds:
        ds.is_active = not ds.is_active
        await db.commit()
        return {"status": "success", "is_active": ds.is_active}
    return {"status": "error", "message": "Dataset not found"}

@router.put("/datasets/{ds_id}")
async def update_dataset(ds_id: int, req: AIDatasetRequest, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AIDataset).filter(AIDataset.id == ds_id))
    ds = result.scalars().first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    ds.name = req.name
    ds.data_type = req.data_type
    ds.content = req.content
    await db.commit()
    logger.info(f"Dataset {ds_id} updated")
    return {"status": "success", "message": "Dataset updated"}

@router.delete("/datasets/{ds_id}")
async def delete_dataset(ds_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(AIDataset).filter(AIDataset.id == ds_id))
    ds = result.scalars().first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await db.delete(ds)
    await db.commit()
    logger.info(f"Dataset {ds_id} deleted")
    return {"status": "success", "message": "Dataset deleted"}

@router.post("/datasets/upload")
async def upload_dataset(
    name: str,
    data_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    admin: User = Depends(get_admin_user)
):
    """Upload and process a knowledge file (CSV/JSON)."""
    logger.info(f"Uploading dataset: {name} ({data_type})")
    
    try:
        content = await file.read()
        processed_content = KnowledgeService.ground_knowledge(data_type, content)
        
        new_ds = AIDataset(
            name=name,
            data_type=data_type,
            content=processed_content
        )
        db.add(new_ds)
        await db.commit()
        await db.refresh(new_ds)
        
        # --- AUDIT LOG ---
        audit = AuditLog(
            user_id=admin.id,
            action="UPLOAD_DATASET",
            resource=f"Dataset {new_ds.id}",
            details=f"Uploaded {data_type} dataset: {name}"
        )
        db.add(audit)
        await db.commit()
        
        return {"status": "success", "dataset_id": new_ds.id}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/intents")
async def get_intent_analytics(db: AsyncSession = Depends(get_async_db)):
    """Analyze intent frequencies from message metadata."""
    # Fetch all AI generated messages to analyze metadata
    result = await db.execute(select(Message).filter(Message.is_ai_generated == True))
    messages = result.scalars().all()
    
    stats = {}
    # Normalization mapping
    NORMALIZATION = {
        "greeting": "Saludo",
        "saludo": "Saludo"
    }

    for msg in messages:
        try:
            meta = json.loads(msg.metadata_json or "{}")
            intent = meta.get("intent", "General")
            # Normalize
            normalized = NORMALIZATION.get(intent.lower(), intent)
            stats[normalized] = stats.get(normalized, 0) + 1
        except:
            continue
            
    # Format for chart consumption
    formatted_stats = [{"intent": k, "count": v} for k, v in stats.items()]
    return sorted(formatted_stats, key=lambda x: x["count"], reverse=True)
@router.get("/audits/security", response_model=List[dict])
async def list_security_audits(db: AsyncSession = Depends(get_async_db)):
    """Fetch security and performance audit logs."""
    result = await db.execute(select(SecurityAudit).order_by(SecurityAudit.timestamp.desc()).limit(100))
    audits = result.scalars().all()
    # Normalize triggered_keywords if it's a JSON string
    res_list = []
    for a in audits:
        obj = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        try:
            obj["triggered_keywords"] = json.loads(a.triggered_keywords or "[]")
        except:
            obj["triggered_keywords"] = []
        res_list.append(obj)
    return res_list

@router.get("/timezones")
def list_timezones():
    """Fetch all available IANA timezones from the system."""
    try:
        return sorted(list(zoneinfo.available_timezones()))
    except Exception as e:
        logger.error(f"Error fetching timezones: {e}")
        return ["UTC", "America/New_York", "Europe/London"] # Fallback

@router.get("/audits/operational", response_model=List[dict])
async def get_operational_audits(db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    """
    Get operational audit logs (Human actions).
    """
    result = await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100))
    logs = result.scalars().all()
    # Manual serialization to handle relationship in a clean dict
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "action": log.action,
            "resource": log.resource,
            "details": log.details,
            "user_id": log.user_id,
            "user": {"username": log.user.username} if log.user else {"username": "System"}
        }
        for log in logs
    ]

@router.get("/security-audits", response_model=List[dict])
async def get_security_audits_legacy(db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    """
    Legacy alias for AI security scan logs.
    """
    return await list_security_audits(db)

# ----------------------------------------------------------------
# Licensing Management
# ----------------------------------------------------------------
class LicenseUploadRequest(BaseModel):
    license_key: str

@router.post("/license")
async def upload_license(req: LicenseUploadRequest, db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    """Upload and activate a new license key."""
    from services.licensing import LicensingService # lazy import to avoid circle
    
    # 1. Verify before saving
    try:
        payload = LicensingService.verify_license(req.license_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # 2. Save to Config
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    
    if not config:
        # Should not happen in normally bootstrapped system
        raise HTTPException(status_code=404, detail="System configuration not found.")
        
    config.license_key = req.license_key
    
    # Audit trail
    log = AuditLog(
        user_id=admin.id,
        action="UPDATE_LICENSE",
        resource="System",
        details=f"Updated license for {payload.get('business_name')} (Plan: {payload.get('plan')})"
    )
    db.add(log)
    await db.commit()
    
    return {"status": "success", "message": "License activated successfully", "payload": payload}

@router.get("/license")
async def get_license_status(db: AsyncSession = Depends(get_async_db), admin: User = Depends(get_admin_user)):
    """Check current license status."""
    from services.licensing import LicensingService
    
    result = await db.execute(select(AIConfig).filter(AIConfig.is_active == True))
    config = result.scalars().first()
    
    if not config or not config.license_key:
        return {"status": "missing", "payload": None}
        
    try:
        payload = LicensingService.verify_license(config.license_key)
        return {"status": "active", "payload": payload}
    except Exception as e:
         return {"status": "invalid", "error": str(e), "payload": None}
