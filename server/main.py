from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import whatsapp, websocket, conversations, admin, auth, system
from database import engine, Base
from prometheus_client import make_asgi_app
from logger import setup_logger

import os

logger = setup_logger("main")

# CORS Configurations
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully")
except Exception as e:
    logger.critical(f"Database initialization failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start worker tasks
    import asyncio
    from services.maintenance import cleanup_stale_messages
    from routers.websocket import start_heartbeat
    
    # Run tasks in background
    cleanup_task = asyncio.create_task(cleanup_stale_messages())
    heartbeat_task = asyncio.create_task(start_heartbeat())
    
    logger.info("Lifespan: Maintenance and Heartbeat tasks started")
    
    yield
    
    # Shutdown: Clean up if needed
    cleanup_task.cancel()
    heartbeat_task.cancel()
    logger.info("Lifespan: Worker tasks stopped")

app = FastAPI(title="WhatsApp AI Dashboard", lifespan=lifespan)


from fastapi import Request
from fastapi.responses import JSONResponse
from services.licensing import LicensingService
from sqlalchemy import select
from database import SessionLocal
from models import AIConfig

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def license_enforcer(request: Request, call_next):
    # Skip license checks for internal/diagnostic/auth routes
    # and crucial admin routes (to upload the license!)
    open_paths = [
        "/auth", 
        "/metrics", 
        "/docs", 
        "/openapi.json", 
        "/admin/license" # Crucial: Allow uploading the key!
    ]
    
    # Root path
    if request.url.path == "/" or request.url.path == "":
        return await call_next(request)
        
    for path in open_paths:
        if request.url.path.startswith(path):
            return await call_next(request)

    # For all other routes, verify license
    try:
        # Retrieve License Key from DB (Synchronous due tomiddleware constraints or use async session properly)
        # Using a fresh sync session for the simplistic middleware check
        with SessionLocal() as db:
            result = db.execute(select(AIConfig).filter(AIConfig.is_active == True))
            config = result.scalars().first()
            
            # If no config or no license key stored (we will add license_key field to AIConfig next)
            # For now, we assume it might be missing
            if not config or not hasattr(config, "license_key") or not config.license_key:
                # If no license is found, block functional routes
                 return JSONResponse(
                    status_code=402, 
                    content={"detail": "No License Key Found. Please activate your product in the Admin Panel."}
                )
            
            # Verify validity
            LicensingService.verify_license(config.license_key)
            
    except Exception as e:
        # If verification fails, return 402 Payment Required
        return JSONResponse(
            status_code=402, 
            content={"detail": str(e)}
        )

    return await call_next(request)

app.include_router(auth.router)
app.include_router(whatsapp.router)
app.include_router(websocket.router)
app.include_router(conversations.router)
app.include_router(admin.router)
app.include_router(system.router)

# Prometheus Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/")
def root():
    logger.debug("Health check endpoint accessed")
    return {"status": "ok", "message": "Backend is running"}
