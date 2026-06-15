"""Smoke tests for rich markdown LaTeX normalization."""

import _bootstrap  # noqa: F401
import sys

from bot.utils.latex import normalize_rich_markdown_latex


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


assert_eq(
    "display-math",
    normalize_rich_markdown_latex(r"块级： \[ \int_0^1 x^2 dx = \frac{1}{3} \]"),
    r"块级： $$\int_0^1 x^2 dx = \frac{1}{3}$$",
)

assert_eq(
    "inline-math",
    normalize_rich_markdown_latex(r"行内： \(x^2 + y^2\)"),
    r"行内： $x^2 + y^2$",
)

assert_eq(
    "code-preserved",
    normalize_rich_markdown_latex(r"`\[x\]` ```latex\n\[\int\]\n```"),
    r"`\[x\]` ```latex\n\[\int\]\n```",
)

print("ALL RICH LATEX SMOKE OK")
