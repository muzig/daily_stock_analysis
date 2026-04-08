#!/usr/bin/env python3
# 手动触发分析测试
import asyncio
from src.config import setup_env
setup_env()

from src.services.task_queue import get_task_queue
from src.config import get_config
from data_provider.base import canonical_stock_code

config = get_config()

async def main():
    stock_code = "562500"
    canon_code = canonical_stock_code(stock_code)
    print(f"触发分析: {stock_code} -> {canon_code}")
    
    queue = get_task_queue()
    from src.analysis_task import run_analysis_task
    task_id = await queue.submit_task(canon_code, run_analysis_task)
    print(f"✅ 任务已提交: task_id={task_id}")
    print("分析正在后台进行，完成后会自动推送到 Telegram，请稍候...")

if __name__ == "__main__":
    asyncio.run(main())
