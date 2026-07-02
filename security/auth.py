from loguru import logger


def sanitize_input(text: str, max_length: int = 4000) -> str:
    """
    清理用户输入

    Args:
        text: 用户输入文本
        max_length: 最大长度

    Returns:
        清理后的文本
    """
    # 截断过长输入
    if len(text) > max_length:
        text = text[:max_length]

    # 移除潜在的命令注入（如果需要）
    # text = text.replace("$(", "").replace("`", "")

    return text.strip()


def detect_sensitive_content(text: str) -> tuple[bool, str]:
    """
    检测敏感内容（简化版）

    Args:
        text: 文本内容

    Returns:
        (是否包含敏感内容, 类型)
    """
    # 简单的敏感词检测（生产环境建议使用专业内容审核服务）
    sensitive_patterns = [
        ("个人信息", ["身份证", "护照号", "银行卡"]),
        ("不当内容", ["暴力", "色情", "赌博"]),
    ]

    text_lower = text.lower()

    for category, keywords in sensitive_patterns:
        for keyword in keywords:
            if keyword in text_lower:
                logger.warning(f"检测到敏感内容: {category} - {keyword}")
                return True, category

    return False, ""
