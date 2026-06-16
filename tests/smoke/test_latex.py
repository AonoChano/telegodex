"""冒烟：bot.utils.latex.normalize_latex 的行为。"""
import sys

import _bootstrap  # noqa: F401

from bot.utils.latex import normalize_latex


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


# 1) 单字符命令替换
assert_eq("integral", normalize_latex("\\int f(x) dx"), "∫ f(x) dx")
assert_eq("sum", normalize_latex("\\sum_{i=1}^n"), "∑_{i=1}^n")
assert_eq("sqrt", normalize_latex("\\sqrt 2"), "√ 2")
assert_eq("alpha", normalize_latex("\\alpha + \\beta"), "α + β")
assert_eq("infty", normalize_latex("x \\to \\infty"), "x → ∞")
assert_eq("Rightarrow", normalize_latex("a \\Rightarrow b"), "a ⇒ b")
assert_eq("leqgeq", normalize_latex("a \\leq b \\geq c"), "a ≤ b ≥ c")
assert_eq("neq", normalize_latex("a \\neq b"), "a ≠ b")
assert_eq("times", normalize_latex("2 \\times 3"), "2 × 3")
assert_eq("div", normalize_latex("6 \\div 2"), "6 ÷ 2")
assert_eq("pm", normalize_latex("\\pm 1"), "± 1")
assert_eq("forall", normalize_latex("\\forall x"), "∀ x")
assert_eq("exists", normalize_latex("\\exists y"), "∃ y")

# 2) 大写希腊字母
assert_eq("Gamma", normalize_latex("\\Gamma(x)"), "Γ(x)")
assert_eq("Omega", normalize_latex("\\Omega"), "Ω")

# 3) 复合命令的反斜杠片段不应被吃（partial vs part）
# 注意 \\partial 长度 >= \\part 长度，所以 \\partial 必须先被匹配
# 实际上我们没有 \\part 映射，所以 \\partial 应被命中
assert_eq("partial", normalize_latex("\\partial f / \\partial x"), "∂ f / ∂ x")

# 4) 代码块必须被原样保留
text = "使用 `\\int f dx` 渲染积分，或 ```latex\n\\int f dx\n``` 整段渲染"
out = normalize_latex(text)
assert_eq(
    "inline-code-preserved",
    out,
    "使用 `\\int f dx` 渲染积分，或 ```latex\n\\int f dx\n``` 整段渲染",
)

# 5) 代码外的 \\int 仍要归一化
text2 = "代码外 \\int 和代码内 `\\int` 应不同处理"
out2 = normalize_latex(text2)
assert "∫" in out2
assert "\\int" in out2  # 行内代码中的 \int 保留
assert_eq("mixed-code", out2, "代码外 ∫ 和代码内 `\\int` 应不同处理")

# 6) 单词内部出现的 \\int（不是独立命令）不应误伤
# 例如 "springtime" 含 'int'，但我们用的是 \\command 形式，正则不匹配
assert_eq("plain-int-word", normalize_latex("springtime"), "springtime")

# 7) 空 / None 输入
assert_eq("empty", normalize_latex(""), "")
assert_eq("none", normalize_latex(None), None)  # 实际是返回 None


# 8) 多条命令连用
assert_eq("combined",
          normalize_latex("\\alpha \\beta \\gamma \\delta"),
          "α β γ δ")

# 9) 完整公式
assert_eq("formula",
          normalize_latex("E = mc^2, \\forall m \\in \\mathbb{R}"),
          "E = mc^2, ∀ m ∈ \\mathbb{R}")  # \mathbb 不在映射中，保留

# 10) \\$ 和 \\_ 是 LaTeX 转义序列，刻意保留（不替换）。
#    _ 在 Rich 渲染下会触发斜体，把数学下标搞坏
assert_eq("escape-dollar", normalize_latex("\\$100"), "\\$100")
assert_eq("escape-underscore", normalize_latex("a\\_b"), "a\\_b")

print("ALL LATEX NORMALIZATION OK")
