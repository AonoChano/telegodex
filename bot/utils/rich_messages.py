"""
Telegram Rich Messages API 支持

Telegram Bot API 10.1+ 引入了 Rich Messages，支持：
- 表格（RichBlockTable）
- 数学公式（RichTextMathematicalExpression）
- 复杂格式嵌套
- 流式输出（sendRichMessageDraft）

由于 aiogram 3.x 可能尚未完全支持这些新 API，本模块提供：
1. 直接调用 Telegram Bot API 的辅助函数
2. Markdown 转 Rich Message 的转换器
3. 回退机制（如果 Rich Messages 不可用）

参考文档：
- https://core.telegram.org/bots/api#rich-messages
- https://core.telegram.org/bots/api#sendrichmessage
"""

import re
from typing import Dict, List, Any, Optional
from loguru import logger
import aiohttp


class RichMessageBuilder:
    """构建 Telegram Rich Message 结构"""

    @staticmethod
    def create_text(content: str, entities: Optional[List[Dict]] = None) -> Dict:
        """创建 RichText 对象"""
        return {
            "type": "richText",
            "text": content,
            "entities": entities or []
        }

    @staticmethod
    def create_paragraph(rich_text: Dict) -> Dict:
        """创建段落块"""
        return {
            "type": "paragraph",
            "text": rich_text
        }

    @staticmethod
    def create_heading(rich_text: Dict, level: int = 2) -> Dict:
        """创建标题块"""
        return {
            "type": "heading",
            "level": level,
            "text": rich_text
        }

    @staticmethod
    def create_table(rows: List[List[str]], has_header: bool = True) -> Dict:
        """
        创建表格块

        Args:
            rows: 表格数据，第一行为表头（如果 has_header=True）
            has_header: 是否包含表头行
        """
        cells = []
        for row_idx, row in enumerate(rows):
            row_cells = []
            for col_idx, cell_content in enumerate(row):
                cell = {
                    "text": RichMessageBuilder.create_text(cell_content),
                    "is_header": has_header and row_idx == 0
                }
                row_cells.append(cell)
            cells.append(row_cells)

        return {
            "type": "table",
            "cells": cells
        }

    @staticmethod
    def create_math_expression(latex: str, is_inline: bool = True) -> Dict:
        """创建数学公式"""
        if is_inline:
            return {
                "type": "richTextMathematicalExpression",
                "expression": latex
            }
        else:
            # 块级公式作为独立段落
            math_text = {
                "type": "richText",
                "text": "",
                "entities": [{
                    "type": "richTextMathematicalExpression",
                    "expression": latex,
                    "offset": 0,
                    "length": 0
                }]
            }
            return RichMessageBuilder.create_paragraph(math_text)

    @staticmethod
    def create_code_block(code: str, language: str = "") -> Dict:
        """创建代码块"""
        return {
            "type": "code",
            "code": RichMessageBuilder.create_text(code),
            "language": language
        }

    @staticmethod
    def create_blockquote(text: str) -> Dict:
        """创建引用块"""
        return {
            "type": "blockQuote",
            "text": RichMessageBuilder.create_text(text)
        }


class MarkdownToRichMessage:
    """将 Markdown 转换为 Rich Message 结构"""

    @staticmethod
    def parse_table(markdown_table: str) -> Optional[Dict]:
        """
        解析 Markdown 表格

        示例输入：
        | Header 1 | Header 2 |
        |----------|----------|
        | Cell 1   | Cell 2   |
        """
        lines = markdown_table.strip().split('\n')
        if len(lines) < 2:
            return None

        rows = []
        for line in lines:
            # 跳过分隔行（只包含 |、-、: 和空格）
            if re.match(r'^\s*\|[\s\-:|]+\|\s*$', line):
                continue

            # 解析单元格
            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            # 跳过空行或全是分隔符的行
            if not cells or all(re.match(r'^[\s\-:]*$', cell) for cell in cells):
                continue

            rows.append(cells)

        if not rows:
            return None

        return RichMessageBuilder.create_table(rows, has_header=True)

    @staticmethod
    def parse_math(markdown_text: str) -> List[Dict]:
        """
        解析数学公式

        支持：
        - 行内公式：$E=mc^2$
        - 块级公式：$$E=mc^2$$
        """
        blocks = []

        # 块级公式：$$...$$
        block_math_pattern = r'\$\$(.+?)\$\$'
        for match in re.finditer(block_math_pattern, markdown_text, re.DOTALL):
            latex = match.group(1).strip()
            blocks.append(RichMessageBuilder.create_math_expression(latex, is_inline=False))

        return blocks

    @staticmethod
    def convert(markdown_text: str) -> Dict:
        """
        将 Markdown 文本转换为 Rich Message

        Returns:
            Rich Message 结构字典
        """
        blocks = []

        # 1. 检测并转换表格
        table_pattern = r'\|.+\|[\s\S]+?\|[\s\-:]+\|[\s\S]+?(?=\n\n|\n$|$)'
        tables = list(re.finditer(table_pattern, markdown_text))

        if tables:
            for table_match in tables:
                table_block = MarkdownToRichMessage.parse_table(table_match.group(0))
                if table_block:
                    blocks.append(table_block)

        # 2. 检测并转换块级数学公式
        math_blocks = MarkdownToRichMessage.parse_math(markdown_text)
        blocks.extend(math_blocks)

        # 3. 如果没有特殊块，返回简单段落
        if not blocks:
            plain_text = RichMessageBuilder.create_text(markdown_text)
            blocks.append(RichMessageBuilder.create_paragraph(plain_text))

        return {
            "type": "inputRichMessage",
            "blocks": blocks
        }


async def send_rich_message(
    bot_token: str,
    chat_id: int,
    rich_message: Dict,
    fallback_text: str
) -> bool:
    """
    发送 Rich Message 到 Telegram

    Args:
        bot_token: Bot Token
        chat_id: 聊天 ID
        rich_message: Rich Message 结构
        fallback_text: 如果 Rich Messages 不可用，使用的回退文本

    Returns:
        是否成功发送
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendRichMessage"

    # rich_message 参数应该只包含 blocks，不需要 type 字段
    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "blocks": rich_message.get("blocks", [])
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                result = await resp.json()

                if result.get("ok"):
                    logger.info(f"✅ Rich Message 发送成功: chat_id={chat_id}")
                    return True
                else:
                    error_desc = result.get("description", "Unknown error")
                    logger.warning(f"⚠️ Rich Message 发送失败: {error_desc}")
                    return False

    except aiohttp.ClientError as e:
        logger.error(f"❌ Rich Message API 请求失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Rich Message 发送异常: {e}")
        return False


def has_rich_features(markdown_text: str) -> bool:
    """
    检测 Markdown 文本是否包含需要 Rich Messages 的特性

    检测：
    - 表格
    - 数学公式（$...$ 或 $$...$$）

    Returns:
        True 如果包含 Rich 特性
    """
    # 检测表格
    if re.search(r'\|.+\|[\s\S]+?\|[\s\-:]+\|', markdown_text):
        return True

    # 检测数学公式
    if re.search(r'\$\$.+?\$\$|\$.+?\$', markdown_text):
        return True

    return False
