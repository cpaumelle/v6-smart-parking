# src/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import v6 routers
from src.routers.v6 import devices, dashboard, gateways, spaces, reservations, tenants, sites
from src.routers import auth, webhooks, websocket
from src.core.database import db
from src.services.background_jobs import start_background_jobs, stop_background_jobs

logging.basicConfig(level=logging.ERROR, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Parking Platform v6",
    description="Multi-tenant parking management system with Row-Level Security",
    version="6.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.example.com",
        "https://app.parking.verdegris.eu",
        "https://parking.verdegris.eu",
        "https://parking.eroundit.eu",
        "https://api-v6.verdegris.eu"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

# Register authentication endpoints
app.include_router(auth.router, tags=["authentication"])

# Register webhook endpoints (no authentication required)
app.include_router(webhooks.router, tags=["webhooks"])
# Register V5 compatibility endpoint for ChirpStack (no prefix)
app.include_router(webhooks.v5_compat_router, tags=["webhooks-v5"])

# Register v6 API endpoints
app.include_router(devices.router, tags=["v6"])
app.include_router(dashboard.router, tags=["v6"])
app.include_router(gateways.router, tags=["v6"])
app.include_router(spaces.router, tags=["v6"])
app.include_router(reservations.router, tags=["v6"])
app.include_router(tenants.router, tags=["v6"])
app.include_router(sites.router, tags=["v6"])

# Register WebSocket endpoint
app.include_router(websocket.router, tags=["websocket"])

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """Initialize database connection and start background jobs on startup"""
    logger.info("Starting Smart Parking Platform v6...")
    await db.connect()
    logger.info("Database connected")
    await start_background_jobs(db)
    logger.info("Background jobs started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await stop_background_jobs()
    await db.disconnect()
    logger.info("Application shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "6.0.0"}
