from bot.handlers.chat_tool_requests import has_chat_tool_request, looks_like_chat_tool_request_prefix


def test_looks_like_chat_tool_request_prefix_accepts_json_and_fenced_json():
    assert looks_like_chat_tool_request_prefix('{"telegodex_tool":"shell","command":"Get-Location"}') is True
    assert looks_like_chat_tool_request_prefix('```json\n{"telegodex_tool":"shell"}\n```') is True


def test_looks_like_chat_tool_request_prefix_rejects_normal_text():
    assert looks_like_chat_tool_request_prefix("please explain shell commands") is False
    assert looks_like_chat_tool_request_prefix("") is False


def test_has_chat_tool_request_uses_full_parser():
    assert has_chat_tool_request('{"telegodex_tool":"shell","command":"Get-ChildItem"}') is True
    assert has_chat_tool_request('{"command":"Get-ChildItem"}') is False
