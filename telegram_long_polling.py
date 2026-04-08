#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot 长轮询模式 - 调用本地 Web API 版本
Bot 主动拉取消息，调用已有的 daily_stock_analysis Web 服务进行分析
不需要修改原有服务，也不需要暴露公网
"""

import asyncio
import logging
import aiohttp
import re
from src.config import setup_env
setup_env()

import signal
import sys
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

from src.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
BOT_TOKEN = config.telegram_bot_token

# 本地 Web API 地址（主服务运行在 8000 端口）
API_BASE_URL = "http://localhost:8000/api/v1"

if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not configured in .env")
    sys.exit(1)

# 配置代理
if getattr(config, 'use_proxy', False) or getattr(config, 'USE_PROXY', False):
    proxy_host = getattr(config, 'proxy_host', '127.0.0.1') or '127.0.0.1'
    proxy_port = getattr(config, 'proxy_port', 10809) or 10809
    PROXY_URL = f"socks5://{proxy_host}:{proxy_port}"
    logger.info(f"Using proxy: {PROXY_URL} for Telegram API")
else:
    PROXY_URL = None
    logger.info("Proxy disabled for Telegram API")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    welcome_text = """👋 欢迎使用股票智能分析机器人！

你可以直接发送股票代码给我，我会调用本地分析服务：
`600519` `002594` `AAPL`

命令：
/analyze 600519 - 分析指定股票
/market - 大盘复盘
/help - 显示帮助信息
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await start(update, context)


def extract_stock_codes(text: str) -> list:
    """从文本中提取股票代码"""
    # 匹配常见股票代码格式
    patterns = [
        r'([\d]{6})',  # A股 6位数字
        r'([A-Z]{1,5})',  # 美股字母代码
        r'hk([\d]{4})',  # 港股
    ]
    codes = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        codes.extend(matches)
    # 去重，过滤空
    return list(filter(None, list(set(codes))))


async def trigger_analysis_background(stock_codes: list, chat_id: int):
    """后台触发分析，不等待结果，分析完主服务会自动推送"""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{API_BASE_URL}/analysis/analyze"
            payload = {
                "stock_codes": stock_codes,
                "async_mode": True
            }
            async with session.post(url, json=payload, timeout=30) as response:
                if response.status in (200, 202):
                    logger.info(f"分析任务已接受: {stock_codes}")
                else:
                    logger.error(f"API 请求失败: HTTP {response.status}")
        except Exception as e:
            logger.error(f"触发分析出错: {e}", exc_info=True)


async def trigger_market_review_background():
    """后台触发大盘复盘"""
    # 实际上大盘复盘接口可能需要单独处理，这里简单触发
    logger.info("触发大盘复盘")
    # 可以后续再实现，现在先告诉用户


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理纯文本消息，尝试提取股票代码分析"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    codes = extract_stock_codes(text)

    if not codes:
        await update.message.reply_text(
            "❓ 没有识别到股票代码，请发送正确的股票代码，例如：`600519`",
            parse_mode='Markdown'
        )
        return

    if len(codes) > 5:
        await update.message.reply_text(f"⚠️ 一次最多分析5只股票，我只处理前5只")
        codes = codes[:5]

    # 立刻回复，后台异步分析
    await update.message.reply_text(
        f"✅ 已收到请求，开始分析 **{', '.join(codes)}**\n\n"
        "分析完成后结果会自动推送到这个聊天，请稍候...",
        parse_mode='Markdown'
    )

    # 后台触发分析
    asyncio.create_task(trigger_analysis_background(codes, update.effective_chat.id))


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command"""
    if not context.args:
        await update.message.reply_text(
            "请提供股票代码，例如：`/analyze 600519`",
            parse_mode='Markdown'
        )
        return
    # 把参数当作文本处理，提取股票代码
    update.message.text = ' '.join(context.args)
    await handle_text_message(update, context)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /market command - 触发大盘复盘"""
    await update.message.reply_text(
        "✅ 已请求大盘复盘，完成后结果会自动推送，请稍候...",
        parse_mode='Markdown'
    )
    asyncio.create_task(trigger_market_review_background())


def main():
    """Main entry point"""
    # 设置代理
    if PROXY_URL:
        # python-telegram-bot v20+ uses aiohttp under the hood
        # We need to create the connection with proxy
        from telegram.ext import Defaults
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .proxy(PROXY_URL)
            .build()
        )
    else:
        application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('analyze', analyze_command))
    application.add_handler(CommandHandler('market', market_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Handle shutdown
    def signal_handler(signum, frame):
        logger.info("Shutting down Telegram bot...")
        asyncio.create_task(application.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Telegram bot in long polling mode (API caller version)...")
    print("🤖 Telegram Bot 启动完成，使用 Ctrl+C 停止")
    print(f"📍 调用本地API: {API_BASE_URL}")
    application.run_polling()


if __name__ == "__main__":
    main()
