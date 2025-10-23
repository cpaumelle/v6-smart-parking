"""API Key Service - API key management with scopes and rate limiting"""

from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import secrets
import hashlib


class APIKeyService:
    """
    API Key management service

    Features:
    - API key generation with scopes
    - Key revocation
    - Rate limiting tracking
    - Usage statistics
    - Expiration management
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def create_api_key(
        self,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
        rate_limit: Optional[int] = None,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Create a new API key

        Args:
            name: Descriptive name for the key
            scopes: List of scopes (e.g., ['devices:read', 'spaces:write'])
            expires_in_days: Optional expiration in days
            rate_limit: Optional rate limit (requests per minute)
            metadata: Additional metadata

        Returns:
            dict: Created API key (includes plain key - only shown once!)
        """

        # Generate API key
        # Format: pk_live_<random_32_chars>
        key_prefix = "pk_live_" if self.tenant.subscription_tier != 'trial' else "pk_test_"
        random_part = secrets.token_urlsafe(32)
        api_key = f"{key_prefix}{random_part}"

        # Hash the key for storage
        key_hash = self._hash_key(api_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Default rate limit based on subscription tier
        if rate_limit is None:
            rate_limits = {
                'basic': 100,
                'professional': 1000,
                'enterprise': 10000
            }
            rate_limit = rate_limits.get(self.tenant.subscription_tier, 100)

        # Validate scopes
        valid_scopes = self._get_valid_scopes()
        invalid_scopes = [s for s in scopes if s not in valid_scopes]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        # Create API key record
        import json
        key_id = await self.db.fetchval("""
            INSERT INTO api_keys (
                tenant_id, user_id, name, key_hash, key_prefix,
                scopes, expires_at, rate_limit_per_minute,
                is_active, metadata, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true, $9, $10, $10)
            RETURNING id
        """,
            self.tenant.tenant_id,
            self.tenant.user_id,
            name,
            key_hash,
            key_prefix,
            json.dumps(scopes),
            expires_at,
            rate_limit,
            json.dumps(metadata or {}),
            datetime.utcnow()
        )

        return {
            "id": str(key_id),
            "name": name,
            "api_key": api_key,  # ONLY TIME THIS IS RETURNED!
            "key_prefix": key_prefix,
            "scopes": scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "rate_limit_per_minute": rate_limit,
            "created_at": datetime.utcnow().isoformat(),
            "warning": "Save this key securely - it will not be shown again!"
        }

    async def list_api_keys(
        self,
        include_revoked: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List API keys for tenant

        Args:
            include_revoked: Include revoked keys

        Returns:
            list: API keys (without plain keys)
        """

        query = """
            SELECT id, tenant_id, user_id, name, key_prefix,
                   scopes, expires_at, rate_limit_per_minute,
                   is_active, last_used_at, usage_count,
                   metadata, created_at, updated_at, revoked_at
            FROM api_keys
            WHERE tenant_id = $1
        """
        params = [self.tenant.tenant_id]

        if not include_revoked:
            query += " AND is_active = true AND revoked_at IS NULL"

        query += " ORDER BY created_at DESC"

        keys = await self.db.fetch(query, *params)

        return [self._api_key_to_dict(k) for k in keys]

    async def get_api_key(self, key_id: UUID) -> Dict[str, Any]:
        """Get API key by ID"""

        key = await self.db.fetchrow("""
            SELECT id, tenant_id, user_id, name, key_prefix,
                   scopes, expires_at, rate_limit_per_minute,
                   is_active, last_used_at, usage_count,
                   metadata, created_at, updated_at, revoked_at
            FROM api_keys
            WHERE id = $1 AND tenant_id = $2
        """, key_id, self.tenant.tenant_id)

        if not key:
            raise ValueError(f"API key {key_id} not found")

        return self._api_key_to_dict(key)

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify and validate an API key

        Args:
            api_key: Plain API key to verify

        Returns:
            dict: Key details if valid, None if invalid
        """

        # Hash the provided key
        key_hash = self._hash_key(api_key)

        # Find key
        key = await self.db.fetchrow("""
            SELECT id, tenant_id, user_id, name, scopes,
                   expires_at, rate_limit_per_minute, is_active,
                   usage_count, last_used_at
            FROM api_keys
            WHERE key_hash = $1
        """, key_hash)

        if not key:
            return None

        # Check if active
        if not key['is_active']:
            return None

        # Check if expired
        if key['expires_at'] and key['expires_at'] < datetime.utcnow():
            # Auto-revoke expired key
            await self.db.execute("""
                UPDATE api_keys
                SET is_active = false, revoked_at = $1
                WHERE id = $2
            """, datetime.utcnow(), key['id'])
            return None

        # Update usage statistics
        await self.db.execute("""
            UPDATE api_keys
            SET usage_count = usage_count + 1,
                last_used_at = $1,
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), key['id'])

        # Check rate limit
        # TODO: Implement Redis-based rate limiting
        # For now, just return the key details

        import json
        scopes = key['scopes']
        if isinstance(scopes, str):
            scopes = json.loads(scopes)

        return {
            "id": str(key['id']),
            "tenant_id": str(key['tenant_id']),
            "user_id": str(key['user_id']),
            "name": key['name'],
            "scopes": scopes,
            "rate_limit_per_minute": key['rate_limit_per_minute']
        }

    async def revoke_api_key(
        self,
        key_id: UUID,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke an API key

        Args:
            key_id: Key ID to revoke
            reason: Optional revocation reason

        Returns:
            dict: Revocation result
        """

        key = await self.db.fetchrow("""
            SELECT id, name FROM api_keys
            WHERE id = $1 AND tenant_id = $2
        """, key_id, self.tenant.tenant_id)

        if not key:
            raise ValueError(f"API key {key_id} not found")

        await self.db.execute("""
            UPDATE api_keys
            SET is_active = false,
                revoked_at = $1,
                revoked_by = $2,
                revocation_reason = $3,
                updated_at = $1
            WHERE id = $4
        """, datetime.utcnow(), self.tenant.user_id, reason, key_id)

        return {
            "success": True,
            "key_id": str(key_id),
            "name": key['name'],
            "revoked_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "message": "API key revoked successfully"
        }

    async def update_api_key(
        self,
        key_id: UUID,
        name: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        rate_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update API key settings (cannot change the key itself)"""

        key = await self.db.fetchrow("""
            SELECT id FROM api_keys
            WHERE id = $1 AND tenant_id = $2
        """, key_id, self.tenant.tenant_id)

        if not key:
            raise ValueError(f"API key {key_id} not found")

        # Build update query
        updates = []
        params = []
        param_count = 0

        if name:
            param_count += 1
            updates.append(f"name = ${param_count}")
            params.append(name)

        if scopes:
            # Validate scopes
            valid_scopes = self._get_valid_scopes()
            invalid_scopes = [s for s in scopes if s not in valid_scopes]
            if invalid_scopes:
                raise ValueError(f"Invalid scopes: {invalid_scopes}")

            import json
            param_count += 1
            updates.append(f"scopes = ${param_count}")
            params.append(json.dumps(scopes))

        if rate_limit is not None:
            param_count += 1
            updates.append(f"rate_limit_per_minute = ${param_count}")
            params.append(rate_limit)

        if not updates:
            raise ValueError("No valid fields to update")

        # Add updated_at
        param_count += 1
        updates.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())

        # Add key_id
        param_count += 1
        params.append(key_id)

        query = f"""
            UPDATE api_keys
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """

        await self.db.execute(query, *params)

        return await self.get_api_key(key_id)

    async def get_usage_stats(self, key_id: UUID) -> Dict[str, Any]:
        """
        Get usage statistics for an API key

        Args:
            key_id: Key ID

        Returns:
            dict: Usage statistics
        """

        key = await self.db.fetchrow("""
            SELECT id, name, usage_count, last_used_at, created_at
            FROM api_keys
            WHERE id = $1 AND tenant_id = $2
        """, key_id, self.tenant.tenant_id)

        if not key:
            raise ValueError(f"API key {key_id} not found")

        # TODO: Get detailed usage from api_key_usage_logs table
        # For now, return basic stats

        days_active = (datetime.utcnow() - key['created_at']).days or 1

        return {
            "key_id": str(key_id),
            "name": key['name'],
            "total_requests": key['usage_count'] or 0,
            "last_used_at": key['last_used_at'].isoformat() if key.get('last_used_at') else None,
            "created_at": key['created_at'].isoformat() if key.get('created_at') else None,
            "days_active": days_active,
            "avg_requests_per_day": round((key['usage_count'] or 0) / days_active, 2),
            "message": "Detailed usage logs require api_key_usage_logs table"
        }

    def _hash_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _get_valid_scopes(self) -> List[str]:
        """Get list of valid API scopes"""
        return [
            'devices:read',
            'devices:write',
            'spaces:read',
            'spaces:write',
            'reservations:read',
            'reservations:write',
            'gateways:read',
            'gateways:write',
            'sites:read',
            'sites:write',
            'analytics:read',
            'webhooks:receive',
            'admin:*'
        ]

    def _api_key_to_dict(self, key) -> Dict[str, Any]:
        """Convert API key row to dictionary (without plain key)"""
        import json

        scopes = key.get('scopes', [])
        if isinstance(scopes, str):
            scopes = json.loads(scopes) if scopes else []

        metadata = key.get('metadata', {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}

        # Check if expired
        is_expired = False
        if key.get('expires_at'):
            is_expired = key['expires_at'] < datetime.utcnow()

        return {
            "id": str(key['id']),
            "tenant_id": str(key['tenant_id']),
            "user_id": str(key['user_id']),
            "name": key['name'],
            "key_prefix": key.get('key_prefix'),
            "scopes": scopes,
            "expires_at": key['expires_at'].isoformat() if key.get('expires_at') else None,
            "is_expired": is_expired,
            "rate_limit_per_minute": key.get('rate_limit_per_minute'),
            "is_active": key['is_active'],
            "last_used_at": key['last_used_at'].isoformat() if key.get('last_used_at') else None,
            "usage_count": key.get('usage_count', 0),
            "metadata": metadata,
            "created_at": key['created_at'].isoformat() if key.get('created_at') else None,
            "revoked_at": key['revoked_at'].isoformat() if key.get('revoked_at') else None
        }
