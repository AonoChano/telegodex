"""
Telegram MarkdownV2 格式化工具

根据 Telegram Bot API 官方文档：
https://core.telegram.org/bots/api#markdownv2-style

需要转义的字符（代码块外）：
_ * [ ] ( ) ~ ` > # + - = | { } . !

特殊支持：
- 代码块可以指定语言（如 python, javascript, latex 等）
- latex 语言会触发 LaTeX 数学公式渲染
"""

import re
from typing import List, Tuple


def format_markdown_v2(text: str) -> str:
    """
    将 AI 输出的 Markdown 文本转换为 Telegram MarkdownV2 格式

    处理逻辑：
    1. 自动检测纯文本 URL 并转换为 Telegram 可识别格式
    2. 识别并保护所有 Markdown 语法结构（代码块、行内代码、链接、粗体、斜体等）
    3. 特别识别 LaTeX 代码块（```latex...```）
    4. 在普通文本区域转义特殊字符
    5. 恢复 Markdown 语法结构

    Args:
        text: AI 输出的原始文本（可能包含 Markdown 语法）

    Returns:
        符合 Telegram MarkdownV2 规范的格式化文本

    支持的格式：
    - **粗体** -> *粗体*
    - *斜体* -> _斜体_
    - `代码` -> `代码`
    - ```language\ncode\n``` -> 代码块（支持语法高亮）
    - ```latex\nformula\n``` -> LaTeX 数学公式渲染
    - [文本](链接) -> 链接
    - ~~删除线~~ -> ~删除线~
    - ||剧透|| -> ||剧透||
    - <blockquote expandable>...</blockquote> -> **>... + || 结尾（MarkdownV2 的
      expandable blockquote 形式，Bot API 7.3+；内部嵌套格式完整保留）
    - http://example.com -> 自动检测并保留（Telegram 自动识别）
    """
    # 需要转义的字符（在普通文本中）
    SPECIAL_CHARS = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    # 保护的 Markdown 结构（使用 \x00 作为占位符，这是不可打印字符，不会被转义）
    protected: List[Tuple[str, str]] = []  # (placeholder, original)

    def protect(match, prefix):
        """保护一个 Markdown 结构"""
        placeholder = f"\x00PROTECTED{prefix}{len(protected)}\x00"
        protected.append((placeholder, match.group(0)))
        return placeholder

    # 步骤 -1: 处理 Telegram 原生 <blockquote expandable>...</blockquote>
    # 这是 Bot API 7.3+ 的可展开引用块：客户端默认只显示前 3 行，展开后看全
    # 文。MarkdownV2 不支持 HTML 标签，需要转成 **>... + || 结尾 的形式：
    #
    #   **>first line
    #   >middle line
    #   >last line||
    #
    # **> 在 MarkdownV2 里有歧义（既可以是粗体+引用，也可能是 empty bold
    # 触发 expandable），所以**显式**用占位符保护，最后整段还原。
    #
    # 处理策略：内部递归走 format_markdown_v2 完成粗体 / 链接 / 行内代码等
    # 转义，然后**重新用占位符保护代码块**（代码块是多行的，split-by-line
    # 加 `>` 会切碎它），再按行加 `>`，最后还原。
    def _convert_expandable_bq(m: re.Match) -> str:
        inner = m.group(1).strip("\n")
        if not inner:
            return ""
        inner_v2 = format_markdown_v2(inner)

        # 重新保护代码块（多行原子），避免被按行 split 切碎
        bq_protected: List[Tuple[str, str]] = []

        def _protect_codeblock_in_bq(m2: re.Match) -> str:
            placeholder = f"\x00EXPBQCODEBLOCK{len(bq_protected)}\x00"
            bq_protected.append((placeholder, m2.group(0)))
            return placeholder

        inner_v2 = re.sub(
            r"```[\s\S]*?```", _protect_codeblock_in_bq, inner_v2
        )

        lines = inner_v2.split("\n")
        if not lines:
            return ""
        formatted = "**>" + lines[0]
        for line in lines[1:]:
            formatted += "\n>" + line
        formatted += "||"

        # 还原代码块
        for placeholder, original in bq_protected:
            formatted = formatted.replace(placeholder, original)

        outer_placeholder = f"\x00PROTECTEDEXPBQ{len(protected)}\x00"
        protected.append((outer_placeholder, formatted))
        return outer_placeholder

    text = re.sub(
        r"<blockquote\s+expandable>(.*?)</blockquote>",
        _convert_expandable_bq,
        text,
        flags=re.DOTALL,
    )

    # 步骤 0: 保护独立的 URL（不在 Markdown 链接中的）
    # 匹配 http:// 或 https:// 开头的 URL，但不在 []() 或 ``  内
    # 这些 URL Telegram 会自动识别为链接，但在 MarkdownV2 中仍需转义特殊字符
    def protect_standalone_url(match):
        url = match.group(0)
        placeholder = f"\x00PROTECTEDURL{len(protected)}\x00"
        # URL 需要转义特殊字符（除了协议分隔符）
        escaped_url = url
        for char in SPECIAL_CHARS:
            if char not in ['(', ')', ':']:  # 保留 : 用于 http:// https://
                escaped_url = escaped_url.replace(char, f'\\{char}')
        protected.append((placeholder, escaped_url))
        return placeholder

    # 先保护 Markdown 链接中的 URL，避免被误识别
    # 支持多行链接格式：[text]\n(url)
    text = re.sub(r'\[([^\]]+)\]\s*\(([^)]+)\)', lambda m: protect(m, 'LINK'), text, flags=re.DOTALL)

    # 然后保护独立的 URL
    text = re.sub(r'(?<!\()(https?://[^\s\)]+)(?!\))', protect_standalone_url, text)

    # 步骤 1: 保护代码块（```...```），包括 LaTeX
    # 匹配格式：```language\ncode\n``` 或 ```\ncode\n```
    text = re.sub(r'```[\s\S]*?```', lambda m: protect(m, 'CODEBLOCK'), text)

    # 步骤 2: 保护行内代码（`...`）
    text = re.sub(r'`[^`\n]+?`', lambda m: protect(m, 'INLINECODE'), text)

    # 步骤 3: 保护粗体（**text**）
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: protect(m, 'BOLD'), text)

    # 步骤 4: 保护斜体（*text*，但要避免与粗体冲突）
    # 使用负向前瞻和负向后顾确保不匹配 **
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', lambda m: protect(m, 'ITALIC'), text)

    # 步骤 5: 保护删除线（~~text~~）
    text = re.sub(r'~~(.+?)~~', lambda m: protect(m, 'STRIKE'), text)

    # 步骤 6: 保护剧透（||text||）
    text = re.sub(r'\|\|(.+?)\|\|', lambda m: protect(m, 'SPOILER'), text)

    # 步骤 6.5: 保护引用块和任务列表
    text = re.sub(r'^>\s*(.*)$', lambda m: protect(m, 'QUOTE'), text, flags=re.MULTILINE)
    text = re.sub(r'^-\s*\[\s*\]\s*(.*)$', lambda m: protect(m, 'TODO'), text, flags=re.MULTILINE)
    text = re.sub(r'^-\s*\[x\]\s*(.*)$', lambda m: protect(m, 'DONE'), text, flags=re.MULTILINE)

    # 步骤 7: 转义普通文本中的所有特殊字符
    for char in SPECIAL_CHARS:
        text = text.replace(char, f'\\{char}')

    # 步骤 8: 恢复所有保护的 Markdown 结构
    for placeholder, original in reversed(protected):
        # 根据不同类型处理原始内容
        if 'CODEBLOCK' in placeholder:
            # 代码块：直接恢复，不转义
            text = text.replace(placeholder, original)

        elif 'INLINECODE' in placeholder:
            # 行内代码：直接恢复，不转义
            text = text.replace(placeholder, original)

        elif 'URL' in placeholder and 'LINK' not in placeholder:
            # 独立 URL：直接恢复，Telegram 会自动识别
            text = text.replace(placeholder, original)

        elif 'LINK' in placeholder:
            # Markdown 链接：需要转义内部文本，但保留语法结构
            # 支持多行链接：[text]\n(url)
            link_match = re.match(r'\[([^\]]+)\]\s*\(([^)]+)\)', original, re.DOTALL)
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)

                # 转义链接文本中的特殊字符（除了已经是 markdown 语法的）
                escaped_text = link_text
                for char in SPECIAL_CHARS:
                    if char not in ['[', ']', '(', ')']:
                        escaped_text = escaped_text.replace(char, f'\\{char}')

                # URL 中也需要转义特殊字符（Telegram MarkdownV2 要求）
                # 但保留 URL 必需的字符：: / ? = & #
                link_url = link_url.strip()
                escaped_url = link_url
                for char in SPECIAL_CHARS:
                    # 排除 URL 中常用的字符
                    if char not in ['(', ')']:  # 括号在 URL 中也需要转义
                        escaped_url = escaped_url.replace(char, f'\\{char}')

                formatted_link = f'[{escaped_text}]({escaped_url})'
                text = text.replace(placeholder, formatted_link)

        elif 'BOLD' in placeholder:
            # 粗体：**text** -> *text*（Telegram 使用单星号）
            bold_match = re.match(r'\*\*(.+?)\*\*', original)
            if bold_match:
                bold_text = bold_match.group(1)
                # 转义内部文本中的特殊字符（除了 *）
                escaped_bold = bold_text
                for char in SPECIAL_CHARS:
                    if char != '*':
                        escaped_bold = escaped_bold.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'*{escaped_bold}*')

        elif 'ITALIC' in placeholder:
            # 斜体：*text* -> _text_（Telegram 使用下划线）
            italic_match = re.match(r'\*(.+?)\*', original)
            if italic_match:
                italic_text = italic_match.group(1)
                escaped_italic = italic_text
                for char in SPECIAL_CHARS:
                    if char not in ['*', '_']:
                        escaped_italic = escaped_italic.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'_{escaped_italic}_')

        elif 'STRIKE' in placeholder:
            # 删除线：~~text~~ -> ~text~（Telegram 使用单波浪号）
            strike_match = re.match(r'~~(.+?)~~', original)
            if strike_match:
                strike_text = strike_match.group(1)
                escaped_strike = strike_text
                for char in SPECIAL_CHARS:
                    if char != '~':
                        escaped_strike = escaped_strike.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'~{escaped_strike}~')

        elif 'SPOILER' in placeholder:
            # 剧透：||text||
            spoiler_match = re.match(r'\|\|(.+?)\|\|', original)
            if spoiler_match:
                spoiler_text = spoiler_match.group(1)
                escaped_spoiler = spoiler_text
                for char in SPECIAL_CHARS:
                    if char != '|':
                        escaped_spoiler = escaped_spoiler.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'||{escaped_spoiler}||')


        elif 'QUOTE' in placeholder:
            quote_match = re.match(r'^>\s*(.*)$', original)
            if quote_match:
                quote_text = quote_match.group(1)
                for char in SPECIAL_CHARS:
                    if char != '>':
                        quote_text = quote_text.replace(char, f'\{char}')
                text = text.replace(placeholder, f'> {quote_text}' if quote_text else '>')

        elif 'TODO' in placeholder:
            todo_match = re.match(r'^-\s*\[\s*\]\s*(.*)$', original)
            if todo_match:
                task_text = todo_match.group(1)
                for char in SPECIAL_CHARS:
                    if char not in ['-', '[', ']']:
                        task_text = task_text.replace(char, f'\{char}')
                text = text.replace(placeholder, f'\- \[ \] {task_text}')

        elif 'DONE' in placeholder:
            done_match = re.match(r'^-\s*\[x\]\s*(.*)$', original)
            if done_match:
                task_text = done_match.group(1)
                for char in SPECIAL_CHARS:
                    if char not in ['-', '[', ']', 'x']:
                        task_text = task_text.replace(char, f'\{char}')
                text = text.replace(placeholder, f'\- \[x\] {task_text}')

        elif 'EXPBQ' in placeholder:
            # <blockquote expandable> 已经在步骤 -1 转成 **>... + || 结尾
            # 的 MarkdownV2 expandable 引用形式，original 已经是最终形态，
            # 原样还原即可
            text = text.replace(placeholder, original)
    return text

    # 步骤 3: 保护链接（[text](url)）
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: protect(m, 'LINK'), text)

    # 步骤 4: 保护粗体（**text**）
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: protect(m, 'BOLD'), text)

    # 步骤 5: 保护斜体（*text*，但要避免与粗体冲突）
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', lambda m: protect(m, 'ITALIC'), text)

    # 步骤 6: 保护删除线（~~text~~）
    text = re.sub(r'~~(.+?)~~', lambda m: protect(m, 'STRIKE'), text)

    # 步骤 7: 保护剧透（||text||）
    text = re.sub(r'\|\|(.+?)\|\|', lambda m: protect(m, 'SPOILER'), text)

    # 步骤 8: 转义普通文本中的所有特殊字符
    for char in SPECIAL_CHARS:
        text = text.replace(char, f'\\{char}')

    # 步骤 9: 恢复所有保护的 Markdown 结构
    for placeholder, original in reversed(protected):
        # 根据不同类型处理原始内容
        if 'CODEBLOCK' in placeholder:
            # 代码块：直接恢复，不转义
            text = text.replace(placeholder, original)

        elif 'INLINECODE' in placeholder:
            # 行内代码：直接恢复，不转义
            text = text.replace(placeholder, original)

        elif 'LINK' in placeholder:
            # 链接：需要转义内部文本，但保留语法结构
            link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', original)
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)

                # 转义链接文本中的特殊字符
                escaped_text = link_text
                for char in SPECIAL_CHARS:
                    if char not in ['[', ']', '(', ')']:
                        escaped_text = escaped_text.replace(char, f'\\{char}')

                # 转义 URL 中的特殊字符（但保留协议和路径分隔符）
                escaped_url = link_url
                for char in ['.', '-', '_', '!']:
                    escaped_url = escaped_url.replace(char, f'\\{char}')

                formatted_link = f'[{escaped_text}]({escaped_url})'
                text = text.replace(placeholder, formatted_link)

        elif 'BOLD' in placeholder:
            # 粗体：**text** -> *text*（Telegram 使用单星号）
            bold_match = re.match(r'\*\*(.+?)\*\*', original)
            if bold_match:
                bold_text = bold_match.group(1)
                # 转义内部文本中的特殊字符（除了 *）
                escaped_bold = bold_text
                for char in SPECIAL_CHARS:
                    if char != '*':
                        escaped_bold = escaped_bold.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'*{escaped_bold}*')

        elif 'ITALIC' in placeholder:
            # 斜体：*text* -> _text_（Telegram 使用下划线）
            italic_match = re.match(r'\*(.+?)\*', original)
            if italic_match:
                italic_text = italic_match.group(1)
                escaped_italic = italic_text
                for char in SPECIAL_CHARS:
                    if char not in ['*', '_']:
                        escaped_italic = escaped_italic.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'_{escaped_italic}_')

        elif 'STRIKE' in placeholder:
            # 删除线：~~text~~ -> ~text~（Telegram 使用单波浪号）
            strike_match = re.match(r'~~(.+?)~~', original)
            if strike_match:
                strike_text = strike_match.group(1)
                escaped_strike = strike_text
                for char in SPECIAL_CHARS:
                    if char != '~':
                        escaped_strike = escaped_strike.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'~{escaped_strike}~')

        elif 'SPOILER' in placeholder:
            # 剧透：||text||
            spoiler_match = re.match(r'\|\|(.+?)\|\|', original)
            if spoiler_match:
                spoiler_text = spoiler_match.group(1)
                escaped_spoiler = spoiler_text
                for char in SPECIAL_CHARS:
                    if char != '|':
                        escaped_spoiler = escaped_spoiler.replace(char, f'\\{char}')
                text = text.replace(placeholder, f'||{escaped_spoiler}||')

    return text


def strip_markdown(text: str) -> str:
    """
    移除所有 Markdown 语法，返回纯文本

    用于日志记录或需要纯文本的场景
    """
    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    # 移除行内代码
    text = re.sub(r'`[^`]+?`', '', text)
    # 移除链接，保留文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 移除粗体、斜体、删除线等
    text = re.sub(r'[*_~]', '', text)

    return text.strip()


# 测试用例
if __name__ == "__main__":
    test_cases = [
        # 纯文本
        "你好！今天天气怎么样？",

        # 带特殊字符
        "这是一个测试(包含括号)和感叹号！",

        # 带粗体和斜体
        "这是**粗体**和*斜体*文本",

        # 带行内代码
        "使用 `print('Hello')` 来输出",

        # 带代码块
        """这是一个 Python 示例：
```python
def hello():
    print("Hello, World!")
```
很简单！""",

        # 带链接
        "访问 [GitHub](https://github.com) 获取更多信息",

        # LaTeX 数学公式（行内）
        "卡片公式为 `$E = 2(\\Delta f + f_m)$`",

        # LaTeX 数学公式（代码块）
        """卡片公式的数学表达式为：
```latex
E = 2(Delta f + f_m)
```
其中各符号含义如下...""",

        # 多行链接格式（AI 有时会生成）
        """访问官方文档：
[卡森公式推导]
(https://en.wikipedia.org/wiki/Carson_bandwidth_rule)
获取详细信息。""",

        # 复杂 LaTeX 示例
        """贝塔函数的积分表达式：
```latex
B = 2f_m(1 + beta) = 2Delta fleft(1 + frac{1}{beta}right)
```
当 $\\beta \\gg 1$ 时，$\\beta \\approx 2f_m$。""",

        # 复杂混合
        """**注意**：这个函数很重要！

使用方法：
```python
result = process(data)
```

详见[文档](https://example.com/docs)。"""
    ]

    print("=== Telegram MarkdownV2 格式化测试 ===\n")
    for i, text in enumerate(test_cases, 1):
        print(f"测试 {i}:")
        print(f"原文: {text}")
        formatted = format_markdown_v2(text)
        print(f"格式化: {formatted}")
        print("-" * 60)
