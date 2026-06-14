from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger


class InMemoryRateLimiter:
    """内存速率限制器（简化版，生产环境建议用 Redis）"""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # user_id -> [timestamp, ...]

    def is_allowed(self, user_id: int) -> tuple[bool, Optional[int]]:
        """
        检查用户是否允许请求

        Args:
            user_id: 用户 ID

        Returns:
            (是否允许, 剩余等待秒数)
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # 清理过期记录
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if ts > cutoff
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            # 计算需要等待的时间
            oldest = self.requests[user_id][0]
            wait_seconds = int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds())
            logger.warning(f"用户 {user_id} 触发速率限制")
            return False, max(wait_seconds, 1)

        # 记录本次请求
        self.requests[user_id].append(now)
        return True, None

    def reset_user(self, user_id: int):
        """重置用户的速率限制"""
        if user_id in self.requests:
            del self.requests[user_id]
            logger.info(f"重置用户 {user_id} 的速率限制")


class RedisRateLimiter:
    """基于 Redis 的速率限制器（生产环境推荐）"""

    def __init__(self, redis_client, max_requests: int, window_seconds: int = 60):
        """
        初始化 Redis 速率限制器

        Args:
            redis_client: Redis 客户端实例
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, user_id: int) -> tuple[bool, Optional[int]]:
        """
        检查用户是否允许请求

        使用 Redis Sorted Set + 滑动窗口算法
        """
        key = f"rate_limit:{user_id}"
        now = datetime.utcnow().timestamp()
        cutoff = now - self.window_seconds

        # 使用 Redis pipeline 提升性能
        pipe = self.redis.pipeline()

        # 移除过期记录
        pipe.zremrangebyscore(key, 0, cutoff)

        # 获取当前计数
        pipe.zcard(key)

        # 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 设置过期时间
        pipe.expire(key, self.window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= self.max_requests:
            # 获取最早的请求时间
            earliest = await self.redis.zrange(key, 0, 0, withscores=True)
            if earliest:
                wait_seconds = int(earliest[0][1] + self.window_seconds - now)
                logger.warning(f"用户 {user_id} 触发速率限制")
                return False, max(wait_seconds, 1)

        return True, None

    async def reset_user(self, user_id: int):
        """重置用户的速率限制"""
        key = f"rate_limit:{user_id}"
        await self.redis.delete(key)
        logger.info(f"重置用户 {user_id} 的速率限制")
