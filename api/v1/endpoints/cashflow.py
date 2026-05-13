# -*- coding: utf-8 -*-
"""
Cashflow analysis API endpoints.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agent.llm_adapter import LLMToolAdapter
from src.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()


class CashFlowAnalyzeRequest(BaseModel):
    description: str = Field(..., min_length=5, description="用户财务状况的自然语言描述")


class CashFlowAssetAllocation(BaseModel):
    name: str
    value: float
    percentage: float


class CashFlowCategoryItem(BaseModel):
    category: str
    inflow: float = 0.0
    outflow: float = 0.0


class CashFlowIncomeItem(BaseModel):
    source: str
    amount: float
    frequency: str = Field(..., pattern="^(monthly|yearly|one-time)$")


class CashFlowExpenseItem(BaseModel):
    category: str
    amount: float
    frequency: str = Field(..., pattern="^(monthly|yearly|one-time)$")


class CashFlowAssetItem(BaseModel):
    type: str
    value: float
    description: str = ""


class CashFlowSummary(BaseModel):
    totalAssets: float
    monthlyIncome: float
    monthlyExpenses: float
    netCashFlow: float
    assetAllocation: List[CashFlowAssetAllocation]
    cashFlowByCategory: List[CashFlowCategoryItem]


class CashFlowBreakdown(BaseModel):
    income: List[CashFlowIncomeItem]
    expenses: List[CashFlowExpenseItem]
    assets: List[CashFlowAssetItem]


class CashFlowResult(BaseModel):
    summary: CashFlowSummary
    breakdown: CashFlowBreakdown
    insights: List[str]


SYSTEM_PROMPT = """你是一位专业的个人财务分析师。请根据用户描述的财务状况，提取并分析其现金流结构，返回标准 JSON 格式。

## 输出格式要求
返回的 JSON 必须严格符合以下 schema：
{
  "summary": {
    "totalAssets": 数字（总资产，单位元）,
    "monthlyIncome": 数字（月均总收入，单位元）,
    "monthlyExpenses": 数字（月均总支出，单位元）,
    "netCashFlow": 数字（月净现金流 = 月收入 - 月支出，单位元）,
    "assetAllocation": [{"name": "资产类型名称", "value": 金额, "percentage": 占比%}, ...],
    "cashFlowByCategory": [{"category": "分类名称", "inflow": 收入, "outflow": 支出}, ...]
  },
  "breakdown": {
    "income": [{"source": "收入来源", "amount": 金额, "frequency": "monthly|yearly|one-time"}, ...],
    "expenses": [{"category": "支出类别", "amount": 金额, "frequency": "monthly|yearly|one-time"}, ...],
    "assets": [{"type": "资产类型", "value": 金额, "description": "描述"}, ...]
  },
  "insights": ["洞察建议1", "洞察建议2", ...]（3-5条针对性财务建议）
}

## 分析规则
1. 所有金额单位统一为人民币（元），不特别标注 currency
2. frequency 字段：规律性收入/支出用 "monthly"，年度收入用 "yearly"，一次性收入/大额资产用 "one-time"
3. totalAssets = 所有资产的当前价值总和（包括存款、股票、房产、基金等）
4. monthlyIncome = 每月实际到账收入（工资、兼职等），不含一次性所得
5. monthlyExpenses = 每月固定支出总和，注意将 yearly/one-time 支出折算为月度等价值
6. netCashFlow = monthlyIncome - monthlyExpenses，为负表示入不敷出
7. assetAllocation 和 cashFlowByCategory 中的 category/name 保持一致命名
8. insights 必须结合用户具体数据生成，不要泛泛而谈

## 重要约束
- 只返回上述 JSON，不要有任何额外的解释文字、markdown 标记或对话性内容
- 如果用户描述不完整，基于合理假设补全并在 insights 中说明假设内容
- JSON 中的数字不要加千分位逗号，直接是纯数字
"""


def _build_llm_adapter(config) -> LLMToolAdapter:
    return LLMToolAdapter(config)


@router.post("/analyze", response_model=CashFlowResult)
async def analyze_cashflow(request: CashFlowAnalyzeRequest):
    """
    Analyze user's financial situation from natural language description.
    Returns structured cash flow data using LLM parsing.
    """
    config = get_config()

    if not config.is_agent_available():
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request.description},
    ]

    def _call_llm():
        adapter = _build_llm_adapter(config)
        return adapter.call_text(
            messages,
            provider=None,
            temperature=0.1,
            max_tokens=4096,
            timeout=60.0,
        )

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, _call_llm)
    except Exception as e:
        logger.error(f"Cashflow LLM call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    if not response.content:
        raise HTTPException(status_code=500, detail="LLM returned empty response")

    raw_content = response.content.strip()

    # Strip markdown code fences if present
    if raw_content.startswith("```"):
        lines = raw_content.split("\n")
        raw_content = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])
        raw_content = raw_content.strip()

    try:
        result_data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}\nRaw content:\n{raw_content}")
        raise HTTPException(status_code=500, detail=f"LLM output is not valid JSON: {str(e)}\nRaw: {raw_content[:200]}")

    try:
        return CashFlowResult(
            summary=CashFlowSummary(**result_data["summary"]),
            breakdown=CashFlowBreakdown(**result_data["breakdown"]),
            insights=result_data.get("insights", []),
        )
    except KeyError as e:
        logger.error(f"LLM response missing required field: {e}, data: {str(result_data)[:300]}")
        raise HTTPException(status_code=500, detail=f"LLM response missing required field: {str(e)}")