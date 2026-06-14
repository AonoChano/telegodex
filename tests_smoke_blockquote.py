"""冒烟：bot.utils.markdown.format_markdown_v2 对 <blockquote expandable> 的转换。

主路径是 sendRichMessage (Rich Markdown + GFM/HTML 直通)，<blockquote expandable>
直接交给 Telegram 渲染。只有当 sendRichMessage 失败回退到 MarkdownV2 时，才需要
format_markdown_v2 把 HTML 标签转成 MarkdownV2 的 **>... + || 结尾 形式。
"""
import sys
from bot.utils.markdown import format_markdown_v2


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}:")
        print(f"  got:  {got!r}")
        print(f"  want: {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


# ---------------------------------------------------------------------------
# 1) 基础转换
# ---------------------------------------------------------------------------

# 单行 expandable blockquote -> **>line||
out = format_markdown_v2("<blockquote expandable>short quote</blockquote>")
assert_eq(
    "single-line",
    out,
    "**>short quote||",
)

# ---------------------------------------------------------------------------
# 2) 多行 expandable blockquote
# ---------------------------------------------------------------------------

src = (
    "<blockquote expandable>\n"
    "Line 1\n"
    "Line 2\n"
    "Line 3\n"
    "Line 4\n"
    "</blockquote>"
)
out = format_markdown_v2(src)
want = "**>Line 1\n>Line 2\n>Line 3\n>Line 4||"
assert_eq("multi-line", out, want)

# ---------------------------------------------------------------------------
# 3) 内部嵌套格式必须保留（粗体 / 链接 / 行内代码 / 代码块）
# ---------------------------------------------------------------------------

src = (
    "<blockquote expandable>\n"
    "This is **bold** and *italic*.\n"
    "</blockquote>"
)
out = format_markdown_v2(src)
# 内部递归走 format_markdown_v2，**bold** 变 *bold*，*italic* 变 _italic_
# 句末 . 被 escape 成 \.；strip 掉首尾空行后是单行
# 整个 expandable 段是占位符保护（`>` 不 escape），末行加 ||
assert_eq(
    "nested-bold-italic",
    out,
    "**>This is *bold* and _italic_\\.||",
)

src = (
    "<blockquote expandable>\n"
    "See [docs](https://example.com) for details.\n"
    "</blockquote>"
)
out = format_markdown_v2(src)
# 链接会被保护，所以最终还原时 [docs](URL) 形式保留
# URL 内的 . 在 MarkdownV2 里需要 escape，末行 . 也 escape
assert "**>See [docs](https://example\\.com) for details\\." in out, f"got: {out!r}"
assert out.endswith("||")

# ---------------------------------------------------------------------------
# 4) 内部特殊字符必须正确 escape
# ---------------------------------------------------------------------------

src = "<blockquote expandable>a.b_c-d=e</blockquote>"
out = format_markdown_v2(src)
# . _ - = 在 MarkdownV2 里需要 escape
assert "a\\.b\\_c\\-d\\=e" in out, f"escape failed: {out!r}"
assert out.startswith("**>")
assert out.endswith("||")

# ---------------------------------------------------------------------------
# 5) expandable 之外的文本也要正常 escape
# ---------------------------------------------------------------------------

src = "Before <blockquote expandable>inside</blockquote> after."
out = format_markdown_v2(src)
assert out.startswith("Before "), f"prefix broken: {out!r}"
assert "**>inside||" in out
assert out.endswith(" after\\."), f"suffix escape broken: {out!r}"

# ---------------------------------------------------------------------------
# 6) 多个 expandable blockquote 共存
# ---------------------------------------------------------------------------

src = (
    "<blockquote expandable>first</blockquote>\n"
    "and\n"
    "<blockquote expandable>second</blockquote>"
)
out = format_markdown_v2(src)
assert "**>first||" in out
assert "**>second||" in out
# 中间的 `and` 保留，前后换行也被保留
assert "and" in out
# 两个 expandable 之间通过换行分隔
assert "\n" in out

# ---------------------------------------------------------------------------
# 7) expandable 内含代码块：代码块必须原样保留
# ---------------------------------------------------------------------------

src = (
    "<blockquote expandable>\n"
    "Example:\n"
    "```python\n"
    "print('hi')\n"
    "```\n"
    "End.\n"
    "</blockquote>"
)
out = format_markdown_v2(src)
# 代码块原样保留（**不**被切碎，**不**被 escape）
assert "```python\nprint('hi')\n```" in out, f"code block broken: {out!r}"
# 引用结构正确
assert out.startswith("**>Example:\n"), f"prefix broken: {out!r}"
# 句末 . 在 MarkdownV2 里要 escape
assert out.endswith(">End\\.||"), f"suffix broken: {out!r}"

# ---------------------------------------------------------------------------
# 8) 行为对齐 Telegram 官方 MarkdownV2 expandable 语法
#
# 官方示例：
#   **>The second expandable block quotation started right after the previous
#   >It is separated from the previous block quotation by an empty bold entity
#   >Expandable block quotation continued
#   >Hidden by default part of the expandable block quotation started
#   >Expandable block quotation continued
#   >The last line of the expandable block quotation with the expandability mark||
#
# 验证我们的输出与官方示例同形：
# ---------------------------------------------------------------------------

src = (
    "<blockquote expandable>\n"
    "The second expandable block quotation started right after the previous\n"
    "It is separated from the previous block quotation by an empty bold entity\n"
    "Expandable block quotation continued\n"
    "Hidden by default part of the expandable block quotation started\n"
    "Expandable block quotation continued\n"
    "The last line of the expandable block quotation with the expandability mark\n"
    "</blockquote>"
)
out = format_markdown_v2(src)
want = (
    "**>The second expandable block quotation started right after the previous\n"
    ">It is separated from the previous block quotation by an empty bold entity\n"
    ">Expandable block quotation continued\n"
    ">Hidden by default part of the expandable block quotation started\n"
    ">Expandable block quotation continued\n"
    ">The last line of the expandable block quotation with the expandability mark||"
)
assert_eq("official-shape", out, want)

# ---------------------------------------------------------------------------
# 9) 普通 blockquote（无 expandable）仍按原行为处理
# ---------------------------------------------------------------------------

src = "> normal quote"
out = format_markdown_v2(src)
# 普通 `> normal quote` 应走原 QUOTE 分支 -> `> normal quote`（普通文本内 . 需 escape）
# 等等，原 markdown.py 的 QUOTE 处理是 if quote_text else '>'，并 escape 所有非 > 字符
# 我们的修改不应影响它
assert "normal quote" in out
assert out.startswith(">")

# ---------------------------------------------------------------------------
# 10) 不匹配的标签：<blockquote> 无 expandable 关键字 -> 不应触发
# ---------------------------------------------------------------------------

# <blockquote>（没有 expandable）不在我们的正则匹配里，会落到普通文本 escape
src = "<blockquote>plain</blockquote>"
out = format_markdown_v2(src)
# 应该被 escape 成 \<blockquote\>plain\</blockquote\>
assert "block" in out
# 验证没有意外触发我们的转换
assert "**>" not in out, f"false positive on plain blockquote: {out!r}"

# ---------------------------------------------------------------------------
# 11) 主路径行为不变（无 expandable 标签的输入应和修改前等价）
# ---------------------------------------------------------------------------

# Regression 保护：确保只新增了 expandable 处理，没破坏其他逻辑
src = "Hello *world*!"
out = format_markdown_v2(src)
# 斜体 *world* -> _world_  ( .  ! 需要 escape)
assert "_world_" in out
assert "\\!" in out

print("OK   all blockquote smoke tests passed")
