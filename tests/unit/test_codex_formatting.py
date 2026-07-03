"""Unit tests for Codex Telegram formatting helpers."""

from __future__ import annotations

from bot.codex import formatting as fmt


def test_trim_status_text_handles_empty_string() -> None:
    assert fmt.trim_status_text("") == ""


def test_trim_status_text_collapses_multiline_whitespace() -> None:
    assert fmt.trim_status_text("  Codex   is\n\n  thinking\t now  ") == "Codex is\n\nthinking now"


def test_trim_status_text_truncates_at_limit() -> None:
    assert fmt.trim_status_text("abcdef", limit=4) == "abc..."


def test_format_command_status_escapes_html_command() -> None:
    status = fmt.format_command_status(command='echo "<ok>" & done')

    assert status.startswith("Codex is running a command...")
    assert "<code>" in status
    assert "&lt;ok&gt;" in status
    assert "&amp;" in status
    assert '"<ok>" &' not in status


def test_format_shell_execution_markdown_uses_rich_details_blocks() -> None:
    text = fmt.format_shell_execution_markdown(
        "Start-Process notepad",
        {"stdout": "opened", "stderr": "warning", "returncode": 1},
    )

    assert "**Shell command failed**" in text
    assert "```powershell\nStart-Process notepad\n```" in text
    assert "**Exit code:** `1`" in text
    assert "<details><summary>stdout</summary>" in text
    assert "<details><summary>stderr</summary>" in text


def test_format_shell_execution_markdown_mentions_no_output() -> None:
    text = fmt.format_shell_execution_markdown("Get-Date", {"returncode": 0})

    assert "**Shell command completed**" in text
    assert "_No output._" in text


def test_format_shell_execution_text_uses_plain_transcript() -> None:
    text = fmt.format_shell_execution_text(
        "Get-ChildItem",
        {"stdout": "file.txt", "stderr": "warning", "returncode": 0},
    )

    assert text.startswith("Shell command completed")
    assert "Command:\nGet-ChildItem" in text
    assert "Exit code: 0" in text
    assert "stdout:\nfile.txt" in text
    assert "stderr:\nwarning" in text
    assert "<details>" not in text
    assert "```" not in text

def test_format_collected_stderr_deduplicates_in_order() -> None:
    assert fmt.format_collected_stderr(
        [
            "Reconnecting... 1/5",
            "Unexpected status 403 Forbidden: quota exhausted",
            "Reconnecting... 1/5",
            "Unexpected status 403 Forbidden: quota exhausted",
            "Reconnecting... 2/5",
        ]
    ) == "\n".join(
        [
            "Reconnecting... 1/5",
            "Unexpected status 403 Forbidden: quota exhausted",
            "Reconnecting... 2/5",
        ]
    )


def test_codex_error_text_moves_raw_stderr_into_runtime_detail() -> None:
    stderr = "Error: unexpected status 403 Forbidden: Only one Codex conversation can run at a time"
    text = "\n".join(
        [
            "_ERROR: Unknown error_",
            "_ERROR: Unknown error_",
            stderr,
        ]
    )

    cleaned = fmt.clean_codex_error_text(text, stderr)
    final = fmt.append_codex_stderr_detail(cleaned, stderr)

    assert "Unknown error" not in final
    assert final.count(stderr) == 1
    assert "Codex runtime detail" in final
    assert "```text" in final


def test_format_codex_retry_status_splits_provider_details() -> None:
    detail = "Unexpected status 403, url: https://example.test, cf-ray: abc123"

    status = fmt.format_codex_retry_status("Reconnecting", detail)

    assert status.splitlines() == [
        "Codex Reconnecting...",
        "Reconnecting",
        "Unexpected status 403",
        "url: https://example.test",
        "cf-ray: abc123",
    ]
