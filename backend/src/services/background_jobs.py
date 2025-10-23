"""Background Jobs Service - Scheduled tasks for V6"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from .reservation_service import ReservationService
from .webhook_service import WebhookService
from ..core.tenant_context_v6 import TenantContextV6

logger = logging.getLogger(__name__)


class BackgroundJobsService:
    """
    Manage background jobs for the platform

    Jobs include:
    - Expire old reservations (every 60 seconds)
    - Process webhook spool (every 60 seconds)
    - Sync ChirpStack devices (every 5 minutes)
    - Cleanup old sensor readings (daily)
    """

    def __init__(self, db):
        self.db = db
        self.running = False
        self._tasks = []

    async def start(self):
        """Start all background jobs"""
        self.running = True
        logger.info("Starting background jobs...")

        # Create tasks for each job
        self._tasks = [
            asyncio.create_task(self._run_periodic_job(
                self.expire_reservations,
                interval=60,
                name="expire_reservations"
            )),
            asyncio.create_task(self._run_periodic_job(
                self.process_webhook_spool,
                interval=60,
                name="process_webhook_spool"
            )),
            asyncio.create_task(self._run_periodic_job(
                self.sync_chirpstack_devices,
                interval=300,  # 5 minutes
                name="sync_chirpstack"
            )),
            asyncio.create_task(self._run_periodic_job(
                self.cleanup_old_readings,
                interval=86400,  # 24 hours
                name="cleanup_readings"
            )),
        ]

        logger.info(f"Started {len(self._tasks)} background jobs")

    async def stop(self):
        """Stop all background jobs"""
        self.running = False
        logger.info("Stopping background jobs...")

        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("All background jobs stopped")

    async def _run_periodic_job(
        self,
        job_func,
        interval: int,
        name: str
    ):
        """
        Run a job periodically

        Args:
            job_func: Async function to run
            interval: Interval in seconds
            name: Job name for logging
        """
        logger.info(f"Starting periodic job: {name} (interval: {interval}s)")

        while self.running:
            try:
                start_time = datetime.utcnow()
                result = await job_func()
                duration = (datetime.utcnow() - start_time).total_seconds()

                logger.info(
                    f"Job '{name}' completed in {duration:.2f}s: {result}"
                )

            except Exception as e:
                logger.error(f"Job '{name}' failed: {str(e)}", exc_info=True)

            # Wait for next run
            await asyncio.sleep(interval)

    async def expire_reservations(self) -> Dict[str, Any]:
        """
        Expire old reservations

        Runs every 60 seconds to mark reservations as expired
        and update space states accordingly
        """
        try:
            # Create platform admin context to access all tenants
            platform_context = await self._get_platform_context()

            service = ReservationService(self.db, platform_context)
            result = await service.expire_old_reservations()

            return {
                "job": "expire_reservations",
                "status": "success",
                **result
            }

        except Exception as e:
            return {
                "job": "expire_reservations",
                "status": "error",
                "error": str(e)
            }

    async def process_webhook_spool(self) -> Dict[str, Any]:
        """
        Process spooled webhook files

        Runs every 60 seconds to retry failed webhook processing
        """
        try:
            webhook_service = WebhookService(self.db)
            result = await webhook_service.process_spool()

            return {
                "job": "process_webhook_spool",
                "status": "success",
                **result
            }

        except Exception as e:
            return {
                "job": "process_webhook_spool",
                "status": "error",
                "error": str(e)
            }

    async def sync_chirpstack_devices(self) -> Dict[str, Any]:
        """
        Sync devices with ChirpStack

        Runs every 5 minutes to:
        - Import new devices from ChirpStack
        - Update device statuses
        - Sync gateway information
        """
        try:
            # TODO: Implement ChirpStack sync
            # from .chirpstack_sync import ChirpStackSyncService
            # sync_service = ChirpStackSyncService(self.db)
            # result = await sync_service.sync_all_tenants()

            return {
                "job": "sync_chirpstack",
                "status": "skipped",
                "message": "ChirpStack sync not yet implemented"
            }

        except Exception as e:
            return {
                "job": "sync_chirpstack",
                "status": "error",
                "error": str(e)
            }

    async def cleanup_old_readings(self) -> Dict[str, Any]:
        """
        Cleanup old sensor readings

        Runs daily to remove sensor readings older than 90 days
        (configurable per tenant)
        """
        try:
            # Default retention: 90 days
            retention_days = 90

            # Use string formatting for INTERVAL as asyncpg doesn't support parameterized intervals
            # RETURNING can't use aggregate functions, so we fetch all IDs and count them
            deleted_ids = await self.db.fetch(f"""
                DELETE FROM sensor_readings
                WHERE received_at < NOW() - INTERVAL '{retention_days} days'
                RETURNING id
            """)

            deleted_count = len(deleted_ids)

            return {
                "job": "cleanup_old_readings",
                "status": "success",
                "deleted_count": deleted_count,
                "retention_days": retention_days
            }

        except Exception as e:
            return {
                "job": "cleanup_old_readings",
                "status": "error",
                "error": str(e)
            }

    async def _get_platform_context(self) -> TenantContextV6:
        """
        Get a platform admin context for background jobs

        This allows background jobs to access all tenants
        """
        from ..core.tenant_context_v6 import TenantContextV6, Role

        return TenantContextV6(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            tenant_name="Platform",
            tenant_slug="platform",
            tenant_type="platform",
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            username="background-jobs",
            role=Role.PLATFORM_ADMIN,
            is_platform_admin=True,
            subscription_tier="enterprise",
            features={},
            limits={}
        )


# Global instance
background_jobs_service: Optional[BackgroundJobsService] = None


async def start_background_jobs(db):
    """Start background jobs service"""
    global background_jobs_service

    if background_jobs_service is None:
        background_jobs_service = BackgroundJobsService(db)
        await background_jobs_service.start()


async def stop_background_jobs():
    """Stop background jobs service"""
    global background_jobs_service

    if background_jobs_service is not None:
        await background_jobs_service.stop()
        background_jobs_service = None
