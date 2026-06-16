from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderSessionData:
    """Per-provider bucket inside a SessionData.

    Fields
    ------
    session_id:
        Provider-specific session identifier (e.g. conversation id or
        Codex thread id).
    message_count:
        Number of messages exchanged in this bucket.
    total_cost_usd:
        Accumulated cost for this bucket.
    total_tokens:
        Accumulated token usage for this bucket.
    """

    session_id: str | None = None
    message_count: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "message_count": self.message_count,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProviderSessionData:
        return cls(
            session_id=data.get("session_id"),
            message_count=data.get("message_count", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class SessionData:
    """In-memory session data keyed by SessionKey.

    provider_sessions maps provider name -> ProviderSessionData so that
    switching providers never loses the context of other providers.
    """

    provider_sessions: dict[str, ProviderSessionData] = field(default_factory=dict)
    active_provider: str | None = None

    def get_or_create_bucket(self, provider_name: str) -> ProviderSessionData:
        """Return the bucket for *provider_name*, creating it if absent."""
        if provider_name not in self.provider_sessions:
            self.provider_sessions[provider_name] = ProviderSessionData()
        return self.provider_sessions[provider_name]

    def set_active_provider(self, provider_name: str) -> ProviderSessionData:
        """Set *provider_name* as active and return its bucket."""
        self.active_provider = provider_name
        return self.get_or_create_bucket(provider_name)

    def to_dict(self) -> dict:
        return {
            "provider_sessions": {
                k: v.to_dict() for k, v in self.provider_sessions.items()
            },
            "active_provider": self.active_provider,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> SessionData:
        if not data:
            return cls()
        buckets = {
            k: ProviderSessionData.from_dict(v)
            for k, v in data.get("provider_sessions", {}).items()
        }
        return cls(
            provider_sessions=buckets,
            active_provider=data.get("active_provider"),
        )
