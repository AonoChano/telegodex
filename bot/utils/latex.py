"""
LaTeX 符号归一化：把 AI 输出的 \\command 形式替换成等价的 Unicode 字符。

- 仅替换\"裸\"反斜杠命令（后面不是字母 / 数字，避免误伤 \\textbf{...} 这类
  复合命令的反斜杠片段）。
- 代码块（```...```）和行内代码（`...`）被原样保留，便于 LaTeX 教程场景下
  仍能展示源码。
- 替换是按\"最长优先\"扫描，避免短命令抢匹配（例如 \\partial 必须在
  \\part 之前）。
- 不会触碰 \\frac{a}{b} 等带花括号的复合命令——这些交给 Telegram
  ``language=latex`` 的代码块渲染更安全。
"""

from __future__ import annotations

import re
from typing import List, Tuple

# 常用 LaTeX → Unicode 映射。覆盖希腊字母 / 常用算子 / 关系 / 箭头 / 集合
# / 逻辑符号，按长度倒序让最长匹配先跑。
LATEX_REPLACEMENTS: dict[str, str] = {
    # 大写希腊字母
    r"\Alpha": "Α",
    r"\Beta": "Β",
    r"\Gamma": "Γ",
    r"\Delta": "Δ",
    r"\Epsilon": "Ε",
    r"\Zeta": "Ζ",
    r"\Eta": "Η",
    r"\Theta": "Θ",
    r"\Iota": "Ι",
    r"\Kappa": "Κ",
    r"\Lambda": "Λ",
    r"\Mu": "Μ",
    r"\Nu": "Ν",
    r"\Xi": "Ξ",
    r"\Pi": "Π",
    r"\Rho": "Ρ",
    r"\Sigma": "Σ",
    r"\Tau": "Τ",
    r"\Upsilon": "Υ",
    r"\Phi": "Φ",
    r"\Chi": "Χ",
    r"\Psi": "Ψ",
    r"\Omega": "Ω",
    # 小写希腊字母
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\varepsilon": "ε",
    r"\zeta": "ζ",
    r"\eta": "η",
    r"\theta": "θ",
    r"\vartheta": "ϑ",
    r"\iota": "ι",
    r"\kappa": "κ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\nu": "ν",
    r"\xi": "ξ",
    r"\pi": "π",
    r"\varpi": "ϖ",
    r"\rho": "ρ",
    r"\varrho": "ϱ",
    r"\sigma": "σ",
    r"\varsigma": "ς",
    r"\tau": "τ",
    r"\upsilon": "υ",
    r"\phi": "φ",
    r"\varphi": "ϕ",
    r"\chi": "χ",
    r"\psi": "ψ",
    r"\omega": "ω",
    # 积分 / 求和 / 乘积
    r"\iint": "∬",
    r"\iiint": "∭",
    r"\oint": "∮",
    r"\int": "∫",
    r"\sum": "∑",
    r"\prod": "∏",
    r"\sqrt": "√",
    r"\partial": "∂",
    r"\nabla": "∇",
    r"\infty": "∞",
    r"\emptyset": "∅",
    # 算子
    r"\times": "×",
    r"\divideontimes": "⋇",
    r"\div": "÷",
    r"\cdot": "·",
    r"\pm": "±",
    r"\mp": "∓",
    r"\ast": "∗",
    r"\star": "⋆",
    r"\circ": "∘",
    r"\bullet": "•",
    # 关系
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\neq": "≠",
    r"\ne": "≠",
    r"\equiv": "≡",
    r"\approx": "≈",
    r"\sim": "∼",
    r"\simeq": "≃",
    r"\cong": "≅",
    r"\propto": "∝",
    r"\ll": "≪",
    r"\gg": "≫",
    r"\prec": "≺",
    r"\succ": "≻",
    # 箭头
    r"\Rightarrow": "⇒",
    r"\Leftarrow": "⇐",
    r"\Leftrightarrow": "⇔",
    r"\rightarrow": "→",
    r"\to": "→",
    r"\leftarrow": "←",
    r"\leftrightarrow": "↔",
    r"\uparrow": "↑",
    r"\downarrow": "↓",
    r"\mapsto": "↦",
    # 集合
    r"\in": "∈",
    r"\notin": "∉",
    r"\subset": "⊂",
    r"\supset": "⊃",
    r"\subseteq": "⊆",
    r"\supseteq": "⊇",
    r"\cup": "∪",
    r"\cap": "∩",
    # 逻辑
    r"\forall": "∀",
    r"\exists": "∃",
    r"\neg": "¬",
    r"\lnot": "¬",
    r"\land": "∧",
    r"\wedge": "∧",
    r"\lor": "∨",
    r"\vee": "∨",
    # 其它常用
    r"\hbar": "ℏ",
    r"\ell": "ℓ",
    r"\Re": "ℜ",
    r"\Im": "ℑ",
    r"\aleph": "ℵ",
    r"\angle": "∠",
    r"\perp": "⊥",
    r"\parallel": "∥",
    r"\therefore": "∴",
    r"\because": "∵",
    r"\cdotp": "·",
    # 注意：\\$ 和 \\_ 是 LaTeX 转义序列而非数学符号，刻意不替换；
    # Rich 渲染下 _ 会触发斜体，反而把 $x_i$ 这种下标搞坏。
}

# 预编译正则：命令后面必须不是字母 / 数字，避免误伤如 \textbar 这种。
_COMPILED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(re.escape(cmd) + r"(?![A-Za-z0-9])"), repl)
    for cmd, repl in sorted(
        LATEX_REPLACEMENTS.items(), key=lambda kv: len(kv[0]), reverse=True
    )
]


def normalize_latex(text: str) -> str:
    """
    把 LaTeX 命名单字符命令替换为 Unicode 等价物。

    代码块 / 行内代码被原样保留，因为这些场景下用户可能就是要展示 LaTeX
    源码。
    """
    if not text:
        return text

    protected: List[Tuple[str, str]] = []

    def protect(match, prefix: str) -> str:
        placeholder = f"\x00LATEX{prefix}{len(protected)}\x00"
        protected.append((placeholder, match.group(0)))
        return placeholder

    # 1) 保护代码块 / 行内代码
    safe = re.sub(r"```[\s\S]*?```", lambda m: protect(m, "BLOCK"), text)
    safe = re.sub(r"`[^`\n]+?`", lambda m: protect(m, "INLINE"), safe)

    # 2) 应用替换
    for pattern, replacement in _COMPILED_PATTERNS:
        safe = pattern.sub(replacement, safe)

    # 3) 还原代码块 / 行内代码
    for placeholder, original in reversed(protected):
        safe = safe.replace(placeholder, original)

    return safe


def normalize_rich_markdown_latex(text: str) -> str:
    """
    Normalize common model LaTeX delimiters for Telegram Rich Markdown.

    Telegram Rich Markdown treats formula source as raw LaTeX and supports
    ``$...$``, ``$$...$$``, and fenced ``math`` blocks. Do not replace LaTeX
    commands with Unicode on this path.
    """
    if not text:
        return text

    protected: List[Tuple[str, str]] = []

    def protect(match, prefix: str) -> str:
        placeholder = f"\x00RICHLATEX{prefix}{len(protected)}\x00"
        protected.append((placeholder, match.group(0)))
        return placeholder

    safe = re.sub(r"```[\s\S]*?```", lambda m: protect(m, "BLOCK"), text)
    safe = re.sub(r"`[^`\n]+?`", lambda m: protect(m, "INLINE"), safe)

    # OpenAI/Claude often emit TeX display delimiters. Telegram Rich Markdown
    # documents block math as $$...$$ and inline math as $...$.
    safe = re.sub(r"\\\[\s*([\s\S]*?)\s*\\\]", r"$$\1$$", safe)
    safe = re.sub(r"\\\(\s*([\s\S]*?)\s*\\\)", r"$\1$", safe)

    for placeholder, original in reversed(protected):
        safe = safe.replace(placeholder, original)

    return safe
