from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime
from datetime import timezone
import os

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Unknown")
    phone_number = Column(String, unique=True, index=True)
    tenant_id = Column(String, default="default", index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    conversations = relationship("Conversation", back_populates="client")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    started_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    auto_ai_enabled = Column(Boolean, default=True) # Manual override for HITL
    tenant_id = Column(String, default="default", index=True)

    client = relationship("Client", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender = Column(String) # "user" (client), "agent" (AI), "system"
    content = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    status = Column(String, default="sent") # pending, sent, delivered, failed
    is_ai_generated = Column(Boolean, default=False)
    confidence = Column(Integer, default=0) # 0-100
    is_violation = Column(Boolean, default=False)
    metadata_json = Column(Text, default="{}") # Stores intent, tone, reasoning in JSON format
    external_id = Column(String, unique=True, nullable=True, index=True) # WhatsApp Message ID (wamid)
    tenant_id = Column(String, default="default", index=True)
    
    # Media Support (Added v11)
    media_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True) # "image", "pdf", "video"
    
    conversation = relationship("Conversation", back_populates="messages")


class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, default="My AI Assistant")
    business_description = Column(Text, default="A professional business.")
    tone = Column(String, default="friendly, concise, and professional")
    rules_json = Column(Text, default="[]") # List of behavioral rules
    
    # Thresholds (0-100)
    auto_respond_threshold = Column(Integer, default=85)
    review_threshold = Column(Integer, default=60)
    auto_send_delay = Column(Integer, default=30) # Delay in seconds before auto-sending
    
    # Context Guardrails
    keywords_json = Column(Text, default="[]") # Allowed topics
    forbidden_topics_json = Column(Text, default="[]") # Topics to ignore
    
    # Multilingual Support
    language_code = Column(String, default="es-CR")
    translate_messages = Column(Boolean, default=False)
    
    # Advanced Prompting (Dynamic Overrides)
    identity_prompt = Column(Text, nullable=True)
    grounding_template = Column(Text, nullable=True)
    intent_rules_json = Column(Text, default="[]") 
    fallback_message = Column(Text, default="I am currently having trouble processing your request.")
    preferred_model = Column(String, default="gpt-4-turbo")
    # Branding & UI/UX (SaaS White-Label)
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, default="#2563eb") # Tailwind blue-600 default
    ui_density = Column(String, default="comfortable") # "compact" or "comfortable"
    
    # Secrets & Integrations (Added v8)
    openai_api_key = Column(String, nullable=True) # Defaults to None (use env or empty)
    openai_api_base = Column(String, default=os.getenv("OPENAI_API_BASE", "http://localhost:1234/v1"))
    whatsapp_api_token = Column(String, nullable=True)
    whatsapp_verify_token = Column(String, nullable=True)
    whatsapp_phone_id = Column(String, nullable=True)
    whatsapp_driver = Column(String, default="mock") # "mock" or "meta"
    
    # Global Settings
    timezone = Column(String, default="UTC") # e.g. "America/Costa_Rica"
    workspace_config = Column(String, default="{}") # JSON storage for UI layout preferences
    suggestions_json = Column(Text, default="[]") # Global quick-reply templates
    tenant_id = Column(String, default="default", index=True)
    
    is_active = Column(Boolean, default=True)
    license_key = Column(Text, nullable=True) # v16 - Licensing
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))


class SecurityAudit(Base):
    __tablename__ = "security_audits"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String)
    input_message = Column(Text)
    output_message = Column(Text)
    domain = Column(String)
    intent = Column(String)
    confidence = Column(Integer)
    latency_ms = Column(Integer)
    model_name = Column(String)
    tokens_used = Column(Integer)
    status = Column(String) # "Passed", "Blocked", "Latency_Violation"
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    reasoning = Column(Text)
    triggered_keywords = Column(Text) # JSON list
    tenant_id = Column(String, default="default", index=True)


class AIDataset(Base):
    __tablename__ = "ai_datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    data_type = Column(String) # "csv", "json", "api", "sql"
    content = Column(Text) # Raw data or configuration URI
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    tenant_id = Column(String, default="default", index=True)


class AIConfigSnapshot(Base):
    __tablename__ = "ai_config_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("ai_configs.id"))
    
    # Snapshot of all config fields
    business_name = Column(String)
    business_description = Column(Text)
    tone = Column(String)
    rules_json = Column(Text)
    auto_respond_threshold = Column(Integer)
    review_threshold = Column(Integer)
    auto_send_delay = Column(Integer)
    keywords_json = Column(Text)
    forbidden_topics_json = Column(Text)
    language_code = Column(String)
    translate_messages = Column(Boolean)
    identity_prompt = Column(Text, nullable=True)
    grounding_template = Column(Text, nullable=True)
    intent_rules_json = Column(Text)
    fallback_message = Column(Text)
    preferred_model = Column(String)
    
    # Snapshot WhatsApp Integration
    whatsapp_driver = Column(String, default="mock")
    whatsapp_phone_id = Column(String, nullable=True)
    
    # Snapshot Branding
    logo_url = Column(String, nullable=True)
    primary_color = Column(String)
    
    # Advanced Version Management
    version_name = Column(String, nullable=True)
    is_locked = Column(Boolean, default=False)
    tenant_id = Column(String, default="default", index=True)
    
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    version_label = Column(String, nullable=True) # DEPRECATED: use version_name


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="operator") # "admin" or "operator"
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String, default="default", index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String) # e.g. "APPROVE_MESSAGE", "EDIT_CONFIG"
    resource = Column(String) # e.g. "Message 123", "AIConfig"
    details = Column(Text, nullable=True) # JSON or descriptive text
    
    user = relationship("User")
