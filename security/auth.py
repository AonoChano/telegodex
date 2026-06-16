
from loguru import logger


class AuthManager:
    """认证和权限管理"""

    def __init__(self, admin_ids: list[int]):
        """
        初始化认证管理器

        Args:
            admin_ids: 管理员用户 ID 列表
        """
        self.admin_ids = set(admin_ids)
        self.blocked_users: set[int] = set()

    def is_admin(self, user_id: int) -> bool:
        """检查是否为管理员"""
        return user_id in self.admin_ids

    def is_blocked(self, user_id: int) -> bool:
        """检查用户是否被封禁"""
        return user_id in self.blocked_users

    def block_user(self, user_id: int):
        """封禁用户"""
        self.blocked_users.add(user_id)
        logger.warning(f"用户 {user_id} 已被封禁")

    def unblock_user(self, user_id: int):
        """解封用户"""
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
            logger.info(f"用户 {user_id} 已解封")

    def add_admin(self, user_id: int):
        """添加管理员"""
        self.admin_ids.add(user_id)
        logger.info(f"用户 {user_id} 已添加为管理员")

    def remove_admin(self, user_id: int):
        """移除管理员"""
        if user_id in self.admin_ids:
            self.admin_ids.remove(user_id)
            logger.info(f"用户 {user_id} 已移除管理员权限")

    def check_permission(self, user_id: int, require_admin: bool = False) -> tuple[bool, str]:
        """
        检查用户权限

        Args:
            user_id: 用户 ID
            require_admin: 是否要求管理员权限

        Returns:
            (是否有权限, 错误消息)
        """
        if self.is_blocked(user_id):
            return False, "您已被封禁，无法使用此功能"

        if require_admin and not self.is_admin(user_id):
            return False, "此功能仅限管理员使用"

        return True, ""


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
