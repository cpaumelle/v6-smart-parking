"""Analytics Service - Reporting, metrics, and data aggregation"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta


class AnalyticsService:
    """
    Analytics and reporting service

    Features:
    - Occupancy trends
    - Revenue reporting (if billing enabled)
    - Device health metrics
    - Usage patterns
    - Custom reports
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def get_occupancy_trends(
        self,
        site_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = 'hourly'
    ) -> Dict[str, Any]:
        """
        Get occupancy trends over time

        Args:
            site_id: Optional site filter
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to now)
            interval: Aggregation interval (hourly, daily, weekly)

        Returns:
            dict: Occupancy trend data
        """

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        # Determine time bucket based on interval
        bucket_format = {
            'hourly': "DATE_TRUNC('hour', created_at)",
            'daily': "DATE_TRUNC('day', created_at)",
            'weekly': "DATE_TRUNC('week', created_at)"
        }.get(interval, "DATE_TRUNC('hour', created_at)")

        # Build query
        # Note: This requires a space_state_history table or sensor_readings
        # For now, return current state counts
        query = f"""
            SELECT
                {bucket_format} as time_bucket,
                COUNT(*) FILTER (WHERE current_state = 'occupied') as occupied,
                COUNT(*) FILTER (WHERE current_state = 'free') as free,
                COUNT(*) FILTER (WHERE current_state = 'reserved') as reserved,
                COUNT(*) as total
            FROM spaces
            WHERE tenant_id = $1
              AND deleted_at IS NULL
        """
        params = [self.tenant.tenant_id]

        if site_id:
            query += f" AND site_id = ${len(params) + 1}"
            params.append(site_id)

        query += f" GROUP BY time_bucket ORDER BY time_bucket"

        trends = await self.db.fetch(query, *params)

        return {
            "site_id": str(site_id) if site_id else None,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": interval,
            "data": [
                {
                    "timestamp": t['time_bucket'].isoformat() if t.get('time_bucket') else None,
                    "occupied": t['occupied'] or 0,
                    "free": t['free'] or 0,
                    "reserved": t['reserved'] or 0,
                    "total": t['total'] or 0,
                    "occupancy_rate": round((t['occupied'] / t['total'] * 100) if t['total'] > 0 else 0, 2)
                }
                for t in trends
            ],
            "message": "Full historical trends require state_history table"
        }

    async def get_reservation_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get reservation statistics

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            dict: Reservation statistics
        """

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_reservations,
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
                COUNT(*) FILTER (WHERE status = 'expired') as expired,
                COUNT(*) FILTER (WHERE checked_in = true) as checked_in,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600) as avg_duration_hours,
                SUM(total_cost) FILTER (WHERE total_cost IS NOT NULL) as total_revenue
            FROM reservations
            WHERE tenant_id = $1
              AND created_at BETWEEN $2 AND $3
        """, self.tenant.tenant_id, start_date, end_date)

        # Get daily breakdown
        daily_stats = await self.db.fetch("""
            SELECT
                DATE_TRUNC('day', created_at) as date,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                SUM(total_cost) FILTER (WHERE total_cost IS NOT NULL) as revenue
            FROM reservations
            WHERE tenant_id = $1
              AND created_at BETWEEN $2 AND $3
            GROUP BY date
            ORDER BY date
        """, self.tenant.tenant_id, start_date, end_date)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": {
                "total_reservations": stats['total_reservations'] or 0,
                "active": stats['active'] or 0,
                "completed": stats['completed'] or 0,
                "cancelled": stats['cancelled'] or 0,
                "expired": stats['expired'] or 0,
                "checked_in": stats['checked_in'] or 0,
                "avg_duration_hours": round(float(stats['avg_duration_hours'] or 0), 2),
                "total_revenue": float(stats['total_revenue'] or 0)
            },
            "daily_breakdown": [
                {
                    "date": d['date'].isoformat() if d['date'] else None,
                    "count": d['count'] or 0,
                    "completed": d['completed'] or 0,
                    "revenue": float(d['revenue'] or 0)
                }
                for d in daily_stats
            ]
        }

    async def get_device_health(self) -> Dict[str, Any]:
        """
        Get device health metrics

        Returns:
            dict: Device health statistics
        """

        # Sensor device health
        sensor_health = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE last_seen_at > NOW() - INTERVAL '1 hour') as active_1h,
                COUNT(*) FILTER (WHERE last_seen_at > NOW() - INTERVAL '24 hours') as active_24h,
                COUNT(*) FILTER (WHERE last_seen_at IS NULL OR last_seen_at < NOW() - INTERVAL '24 hours') as inactive,
                AVG(EXTRACT(EPOCH FROM (NOW() - last_seen_at)) / 60) FILTER (WHERE last_seen_at IS NOT NULL) as avg_silence_minutes
            FROM sensor_devices
            WHERE tenant_id = $1
        """, self.tenant.tenant_id)

        # Display device health
        display_health = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'inactive') as inactive,
                COUNT(*) FILTER (WHERE assigned_space_id IS NOT NULL) as assigned
            FROM display_devices
            WHERE tenant_id = $1
        """, self.tenant.tenant_id)

        # Downlink queue health
        downlink_stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_commands,
                COUNT(*) FILTER (WHERE status = 'queued') as queued,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'sent') as sent,
                COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(EXTRACT(EPOCH FROM (sent_at - created_at))) FILTER (WHERE sent_at IS NOT NULL) as avg_queue_time_seconds
            FROM downlink_queue
            WHERE tenant_id = $1
              AND created_at > NOW() - INTERVAL '24 hours'
        """, self.tenant.tenant_id)

        return {
            "sensors": {
                "total": sensor_health['total'] or 0,
                "active_1h": sensor_health['active_1h'] or 0,
                "active_24h": sensor_health['active_24h'] or 0,
                "inactive": sensor_health['inactive'] or 0,
                "avg_silence_minutes": round(float(sensor_health['avg_silence_minutes'] or 0), 2),
                "health_score": round((sensor_health['active_24h'] / sensor_health['total'] * 100) if sensor_health['total'] > 0 else 0, 2)
            },
            "displays": {
                "total": display_health['total'] or 0,
                "active": display_health['active'] or 0,
                "inactive": display_health['inactive'] or 0,
                "assigned": display_health['assigned'] or 0
            },
            "downlink_queue": {
                "total_commands_24h": downlink_stats['total_commands'] or 0,
                "queued": downlink_stats['queued'] or 0,
                "pending": downlink_stats['pending'] or 0,
                "sent": downlink_stats['sent'] or 0,
                "confirmed": downlink_stats['confirmed'] or 0,
                "failed": downlink_stats['failed'] or 0,
                "avg_queue_time_seconds": round(float(downlink_stats['avg_queue_time_seconds'] or 0), 2)
            },
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_usage_patterns(
        self,
        site_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze usage patterns

        Args:
            site_id: Optional site filter
            days: Number of days to analyze

        Returns:
            dict: Usage pattern analysis
        """

        start_date = datetime.utcnow() - timedelta(days=days)

        # Peak hours analysis (based on reservations)
        hourly_usage = await self.db.fetch("""
            SELECT
                EXTRACT(HOUR FROM start_time) as hour,
                COUNT(*) as reservation_count,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600) as avg_duration_hours
            FROM reservations
            WHERE tenant_id = $1
              AND created_at >= $2
            GROUP BY hour
            ORDER BY hour
        """, self.tenant.tenant_id, start_date)

        # Day of week analysis
        daily_usage = await self.db.fetch("""
            SELECT
                EXTRACT(DOW FROM start_time) as day_of_week,
                COUNT(*) as reservation_count
            FROM reservations
            WHERE tenant_id = $1
              AND created_at >= $2
            GROUP BY day_of_week
            ORDER BY day_of_week
        """, self.tenant.tenant_id, start_date)

        # Most popular spaces
        popular_spaces = await self.db.fetch("""
            SELECT
                s.id,
                s.code,
                s.name,
                COUNT(r.id) as reservation_count,
                AVG(EXTRACT(EPOCH FROM (r.end_time - r.start_time)) / 3600) as avg_duration_hours
            FROM spaces s
            LEFT JOIN reservations r ON r.space_id = s.id AND r.created_at >= $2
            WHERE s.tenant_id = $1
              AND s.deleted_at IS NULL
            GROUP BY s.id, s.code, s.name
            ORDER BY reservation_count DESC
            LIMIT 10
        """, self.tenant.tenant_id, start_date)

        # Day names
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        return {
            "analysis_period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "peak_hours": [
                {
                    "hour": int(h['hour']),
                    "reservation_count": h['reservation_count'] or 0,
                    "avg_duration_hours": round(float(h['avg_duration_hours'] or 0), 2)
                }
                for h in hourly_usage
            ],
            "day_of_week": [
                {
                    "day": day_names[int(d['day_of_week'])],
                    "day_number": int(d['day_of_week']),
                    "reservation_count": d['reservation_count'] or 0
                }
                for d in daily_usage
            ],
            "popular_spaces": [
                {
                    "space_id": str(s['id']),
                    "space_code": s['code'],
                    "space_name": s['name'],
                    "reservation_count": s['reservation_count'] or 0,
                    "avg_duration_hours": round(float(s['avg_duration_hours'] or 0), 2)
                }
                for s in popular_spaces
            ],
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_tenant_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive tenant summary

        Returns:
            dict: Complete tenant overview
        """

        # Get all stats in parallel
        import asyncio

        device_health, reservation_stats, current_occupancy = await asyncio.gather(
            self.get_device_health(),
            self.get_reservation_stats(),
            self._get_current_occupancy()
        )

        return {
            "tenant_id": str(self.tenant.tenant_id),
            "tenant_name": self.tenant.tenant_name,
            "generated_at": datetime.utcnow().isoformat(),
            "occupancy": current_occupancy,
            "device_health": device_health,
            "reservations": reservation_stats,
            "subscription_tier": self.tenant.subscription_tier
        }

    async def _get_current_occupancy(self) -> Dict[str, Any]:
        """Get current occupancy snapshot"""

        stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_spaces,
                COUNT(*) FILTER (WHERE current_state = 'free') as free,
                COUNT(*) FILTER (WHERE current_state = 'occupied') as occupied,
                COUNT(*) FILTER (WHERE current_state = 'reserved') as reserved,
                COUNT(*) FILTER (WHERE current_state = 'maintenance') as maintenance
            FROM spaces
            WHERE tenant_id = $1 AND deleted_at IS NULL
        """, self.tenant.tenant_id)

        total = stats['total_spaces'] or 0
        occupied = stats['occupied'] or 0

        return {
            "total_spaces": total,
            "free": stats['free'] or 0,
            "occupied": occupied,
            "reserved": stats['reserved'] or 0,
            "maintenance": stats['maintenance'] or 0,
            "occupancy_rate": round((occupied / total * 100) if total > 0 else 0, 2)
        }
