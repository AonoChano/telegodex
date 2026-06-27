from __future__ import annotations

import pytest

from core.orchestrator.shell_pipeline import (
    build_shell_proposal_messages,
    parse_shell_command_proposal,
    parse_shell_request,
)


def test_parse_shell_request_defaults_to_ai_mode() -> None:
    request = parse_shell_request("list recent modified files")

    assert request.mode == "ai"
    assert request.text == "list recent modified files"


@pytest.mark.parametrize("text", ["!git status", "-- git status"])
def test_parse_shell_request_supports_raw_mode(text: str) -> None:
    request = parse_shell_request(text)

    assert request.mode == "raw"
    assert request.text == "git status"


def test_build_shell_proposal_messages_requests_json() -> None:
    messages = build_shell_proposal_messages("show current directory")

    assert len(messages) == 2
    assert "Return JSON only" in messages[0].content
    assert "show current directory" in messages[1].content


def test_parse_shell_command_proposal_accepts_fenced_json() -> None:
    proposal = parse_shell_command_proposal(
        '```json\n{"command": "Get-Location", "explanation": "Shows cwd", "risk": "Read-only"}\n```'
    )

    assert proposal.command == "Get-Location"
    assert proposal.explanation == "Shows cwd"
    assert proposal.risk == "Read-only"


def test_parse_shell_command_proposal_rejects_non_json() -> None:
    with pytest.raises(ValueError):
        parse_shell_command_proposal("run Get-Location")
