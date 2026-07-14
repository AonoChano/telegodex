"""Structural guards for the Telegram-facing Codex handler."""

from __future__ import annotations

import ast
from pathlib import Path

CODEX_HANDLER = Path(__file__).resolve().parents[2] / "bot" / "handlers" / "codex.py"

BANNED_IMPORT_PREFIXES = (
    "extensions.codex",
    "sqlalchemy",
    "storage",
    "providers",
    "subprocess",
)
ALLOWED_IMPORT_MODULES = {
    "extensions.codex.daemon",
    "storage.context_manager",
}
BANNED_CALL_NAMES = {
    "create_subprocess_exec",
    "create_subprocess_shell",
    "Popen",
    "run",
    "select",
}
BANNED_DIRECT_DB_METHODS = {
    "add",
    "commit",
    "delete",
    "execute",
    "flush",
    "rollback",
}


def _parse_handler() -> ast.Module:
    return ast.parse(CODEX_HANDLER.read_text(encoding="utf-8"), filename=str(CODEX_HANDLER))


def _imported_modules(tree: ast.AST) -> list[tuple[str, int]]:
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append((node.module, node.lineno))
    return modules


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*_attribute_chain(node.value), node.attr)
    return ()


def test_codex_handler_does_not_import_business_implementations() -> None:
    """The Telegram adapter must delegate persistence and execution."""
    violations = [
        (module, line)
        for module, line in _imported_modules(_parse_handler())
        if module not in ALLOWED_IMPORT_MODULES
        and any(
            module == prefix or module.startswith(f"{prefix}.")
            for prefix in BANNED_IMPORT_PREFIXES
        )
    ]

    assert not violations, (
        "bot/handlers/codex.py imported a persistence, provider, or process "
        f"implementation instead of delegating it: {violations}"
    )


def test_codex_handler_does_not_execute_database_or_runtime_calls() -> None:
    """Catch direct DB, subprocess, and app-server calls in the handler."""
    violations: list[tuple[str, int]] = []
    for node in ast.walk(_parse_handler()):
        if not isinstance(node, ast.Call):
            continue
        chain = _attribute_chain(node.func)
        if not chain:
            continue

        call_name = chain[-1]
        if call_name in BANNED_CALL_NAMES or call_name == "send_request":
            violations.append((".".join(chain), node.lineno))
            continue
        if (
            len(chain) >= 3
            and chain[-3:-1] == ("context_manager", "session")
            and call_name in BANNED_DIRECT_DB_METHODS
        ):
            violations.append((".".join(chain), node.lineno))

    assert not violations, (
        "bot/handlers/codex.py performed business work directly; move it to "
        f"bot.codex, core.orchestrator, or extensions.codex: {violations}"
    )


def test_codex_handler_keeps_expected_delegation_seams() -> None:
    """Prevent the guard from passing after accidental adapter deletion."""
    imported = {module for module, _ in _imported_modules(_parse_handler())}

    assert "bot.codex" in imported
    assert "core.orchestrator" in imported
    assert "extensions.codex.daemon" in imported
