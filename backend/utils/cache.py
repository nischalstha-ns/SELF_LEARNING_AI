import json
from typing import Optional

class CacheService:
    def __init__(self):
        # Simple in-memory cache (replace with Redis in production)
        self._cache = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        self._cache[key] = value
        # In production, implement TTL with Redis
    
    async def delete(self, key: str):
        self._cache.pop(key, None)