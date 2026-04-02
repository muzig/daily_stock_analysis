# -*- coding: utf-8 -*-
"""
===================================
Telegram 平台适配器
===================================

负责：
1. 验证 Telegram Webhook 请求（通过 Secret Token）
2. 解析 Telegram 消息为统一格式
3. 将响应转换为 Telegram 格式

Telegram Bot API 文档：
https://core.telegram.org/bots/api
"""

import hashlib
import hmac
import logging
from typing import Dict, Any, Optional

from bot.platforms.base import BotPlatform
from bot.models import BotMessage, BotResponse, WebhookResponse, ChatType

logger = logging.getLogger(__name__)


class TelegramPlatform(BotPlatform):
    """
    Telegram 平台适配器

    支持：
    - 私聊消息
    - 群聊消息
    - Webhook Secret Token 验证

    配置要求：
    - TELEGRAM_BOT_TOKEN: Bot Token（从 @BotFather 获取）
    - TELEGRAM_WEBHOOK_SECRET: Webhook Secret Token（可选，用于验证请求）
    """

    def __init__(self):
        from src.config import get_config
        config = get_config()

        self._bot_token = getattr(config, 'telegram_bot_token', None)
        self._webhook_secret = getattr(config, 'telegram_webhook_secret', None)

    @property
    def platform_name(self) -> str:
        """平台标识名称"""
        return "telegram"

    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        验证 Telegram Webhook 请求

        Telegram Webhook 验证机制：
        1. 设置 Webhook 时指定 secret_token
        2. Telegram 会在请求头 X-Telegram-Bot-Api-Secret-Token 中携带该 token
        3. 服务端验证该 token 是否匹配

        Args:
            headers: HTTP 请求头
            body: 请求体原始字节

        Returns:
            签名是否有效
        """
        if not self._webhook_secret:
            logger.debug("[Telegram] 未配置 webhook_secret，跳过签名验证")
            return True

        # 从请求头获取 Telegram 发送的 secret token
        telegram_secret = headers.get('x-telegram-bot-api-secret-token', '')

        if not telegram_secret:
            logger.warning("[Telegram] 请求头中缺少 X-Telegram-Bot-Api-Secret-Token")
            return False

        # 验证 secret token
        if telegram_secret != self._webhook_secret:
            logger.warning("[Telegram] Secret Token 验证失败")
            return False

        return True

    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """
        解析 Telegram 消息为统一格式

        Telegram Update 格式：
        {
            "update_id": 123456789,
            "message": {
                "message_id": 123,
                "from": {
                    "id": 987654321,
                    "is_bot": false,
                    "first_name": "User",
                    "username": "testuser"
                },
                "chat": {
                    "id": 987654321,
                    "first_name": "User",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1609459200,
                "text": "/analyze 600519"
            }
        }

        Args:
            data: 解析后的 JSON 数据（Telegram Update 对象）

        Returns:
            BotMessage 对象，或 None（不需要处理的消息）
        """
        # 检查是否包含消息
        message = data.get('message')
        if not message:
            logger.debug("[Telegram] 非消息更新，忽略")
            return None

        # 提取消息内容
        text = message.get('text', '').strip()
        if not text:
            logger.debug("[Telegram] 空文本消息，忽略")
            return None

        # 提取用户信息
        from_user = message.get('from', {})
        user_id = str(from_user.get('id', ''))
        user_name = from_user.get('username') or from_user.get('first_name', 'unknown')

        # 提取聊天信息
        chat = message.get('chat', {})
        chat_id = str(chat.get('id', ''))
        chat_type_str = chat.get('type', 'private')

        # 确定会话类型
        if chat_type_str == 'private':
            chat_type = ChatType.PRIVATE
        elif chat_type_str in ('group', 'supergroup', 'channel'):
            chat_type = ChatType.GROUP
        else:
            chat_type = ChatType.UNKNOWN

        # 提取消息 ID
        message_id = str(message.get('message_id', ''))

        # 提取附件信息（如果有）
        attachment_urls = []

        # 处理照片附件
        photos = message.get('photo', [])
        if photos:
            # 取最大尺寸的照片
            largest_photo = max(photos, key=lambda p: p.get('file_size', 0))
            file_id = largest_photo.get('file_id', '')
            if file_id:
                attachment_urls.append(f"photo:{file_id}")

        # 处理文档附件
        document = message.get('document')
        if document:
            file_id = document.get('file_id', '')
            file_name = document.get('file_name', 'unknown')
            if file_id:
                attachment_urls.append(f"document:{file_id}:{file_name}")

        # 构建 BotMessage 对象
        bot_message = BotMessage(
            platform="telegram",
            message_id=message_id,
            user_id=user_id,
            user_name=user_name,
            chat_id=chat_id,
            chat_type=chat_type,
            content=text,
            raw_content=text,
            mentioned=False,  # Telegram 使用 /command 格式，不需要 @mention
            mentions=[],
            timestamp=message.get('date'),
            raw_data={
                "update_id": data.get('update_id'),
                "message_id": message_id,
                "chat_id": chat_id,
                "chat_type": chat_type_str,
                "from": from_user,
                "text": text,
                "date": message.get('date'),
                "attachments": attachment_urls,
                "reply_to_message": message.get('reply_to_message'),
            }
        )

        return bot_message

    def format_response(
        self,
        response: BotResponse,
        message: BotMessage
    ) -> WebhookResponse:
        """
        将统一响应转换为 Telegram 格式

        Args:
            response: 统一响应对象
            message: 原始消息对象（用于获取 chat_id 等信息）

        Returns:
            WebhookResponse 对象
        """
        chat_id = message.chat_id
        text = response.text if hasattr(response, 'text') else str(response)

        # 构建 Telegram sendMessage 请求参数
        telegram_response = {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        # 如果是回复消息，添加 reply_to_message_id
        if response.reply_to_message and message.message_id:
            telegram_response["reply_to_message_id"] = message.message_id

        return WebhookResponse.success(telegram_response)

    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """
        处理 Telegram 验证请求

        Telegram 不需要像 Discord 那样进行 URL 验证，
        但我们可以通过 setWebhook API 的响应来确认配置正确。

        Args:
            data: 请求数据

        Returns:
            验证响应，或 None（不是验证请求）
        """
        # Telegram 没有验证挑战机制
        return None


def get_telegram_file_url(bot_token: str, file_id: str) -> Optional[str]:
    """
    获取 Telegram 文件的下载 URL

    Args:
        bot_token: Bot Token
        file_id: 文件 ID

    Returns:
        文件下载 URL，或 None（获取失败）
    """
    import requests

    try:
        api_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.post(api_url, json={"file_id": file_id}, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                file_path = result['result']['file_path']
                return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

        logger.error(f"[Telegram] 获取文件 URL 失败: {response.text}")
        return None

    except Exception as e:
        logger.error(f"[Telegram] 获取文件 URL 异常: {e}")
        return None
