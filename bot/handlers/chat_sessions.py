"""Session bucket helpers for normal chat handlers."""

from sqlalchemy import select

from core.session import SessionData, SessionKey, session_manager
from storage import ContextManager
from storage.models import Conversation


async def load_session_data(
    conversation: Conversation,
    session_key: SessionKey,
) -> SessionData:
    """Load ``SessionData`` from *conversation* or memory."""
    data = session_manager.get_session_data(session_key)
    if data is None:
        data = SessionData.from_dict(conversation.provider_sessions)
        session_manager.set_session_data(session_key, data)
    return data


async def save_session_data(
    conversation: Conversation,
    session_key: SessionKey,
) -> None:
    """Persist ``SessionData`` back to *conversation*."""
    data = session_manager.get_session_data(session_key)
    if data is not None:
        conversation.provider_sessions = data.to_dict()


async def resolve_provider_conversation(
    context_manager: ContextManager,
    session_key: SessionKey,
    session_data: SessionData,
    user_id: int,
    thread_id: int | None,
    provider_name: str,
) -> Conversation:
    """Return the conversation for *provider_name*, creating one if needed.

    Uses the provider bucket ``session_id`` when available so that switching
    providers never loses context.
    """
    bucket = session_data.get_or_create_bucket(provider_name)

    if bucket.session_id:
        stmt = select(Conversation).where(Conversation.id == int(bucket.session_id))
        result = await context_manager.session.execute(stmt)
        conv = result.scalar_one_or_none()
        if conv is not None:
            if not conv.is_active:
                conv.is_active = True
            return conv

    conv = await context_manager.create_new_conversation(user_id, thread_id=thread_id, chat_id=session_key.chat_id)
    bucket.session_id = str(conv.id)
    return conv
