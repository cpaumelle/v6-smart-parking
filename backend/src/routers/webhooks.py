"""Webhook Router - Handle external webhooks from ChirpStack"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from datetime import datetime

from ..core.database import get_db
from ..services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/chirpstack/uplink")
async def chirpstack_uplink(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """
    ChirpStack uplink webhook endpoint

    Receives sensor uplink messages from ChirpStack with:
    - Signature validation
    - Deduplication by frame counter
    - Automatic space state updates
    - Orphan device tracking

    Headers:
        X-Signature: HMAC-SHA256 signature of request body

    Body: ChirpStack uplink JSON payload
    """
    # Get raw body for signature validation
    raw_body = await request.body()

    # Parse JSON
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Get database connection
    db = await get_db()

    # Create webhook service
    webhook_service = WebhookService(db)

    # Validate signature
    if x_signature:
        if not webhook_service.validate_signature(raw_body, x_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Process uplink
    try:
        result = await webhook_service.process_uplink(payload, x_signature)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chirpstack/join")
async def chirpstack_join(request: Request):
    """
    ChirpStack join webhook endpoint

    Receives OTAA join notifications from ChirpStack.
    Can be used to auto-provision devices on first join.
    """
    try:
        payload = await request.json()
        dev_eui = payload.get("deviceInfo", {}).get("devEui", "").upper()

        db = await get_db()

        # Check if device exists
        device = await db.fetchrow("""
            SELECT id, status FROM sensor_devices
            WHERE dev_eui = $1
        """, dev_eui)

        if device:
            # Update status to active on join
            await db.execute("""
                UPDATE sensor_devices
                SET status = 'active',
                    lifecycle_state = 'operational',
                    last_seen_at = $1,
                    updated_at = $1
                WHERE dev_eui = $2
            """, datetime.utcnow(), dev_eui)

            return {
                "status": "updated",
                "dev_eui": dev_eui,
                "message": "Device activated on join"
            }
        else:
            # Log orphan join
            return {
                "status": "unknown_device",
                "dev_eui": dev_eui,
                "message": "Device not found (consider auto-provisioning)"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def webhook_health():
    """
    Webhook health check

    Useful for ChirpStack to verify the webhook endpoint is reachable
    """
    return {
        "status": "healthy",
        "service": "parking-webhooks",
        "timestamp": datetime.utcnow().isoformat()
    }
