# -*- coding: utf-8 -*-
"""Portfolio API schemas."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PortfolioAccountCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    broker: Optional[str] = Field(None, max_length=64)
    market: Literal["cn", "hk", "us"] = "cn"
    base_currency: str = Field("CNY", min_length=3, max_length=8)
    owner_id: Optional[str] = Field(None, max_length=64)


class PortfolioAccountUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    broker: Optional[str] = Field(None, max_length=64)
    market: Optional[Literal["cn", "hk", "us"]] = None
    base_currency: Optional[str] = Field(None, min_length=3, max_length=8)
    owner_id: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class PortfolioAccountItem(BaseModel):
    id: int
    owner_id: Optional[str] = None
    name: str
    broker: Optional[str] = None
    market: str
    base_currency: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioAccountListResponse(BaseModel):
    accounts: List[PortfolioAccountItem] = Field(default_factory=list)


class PortfolioTradeCreateRequest(BaseModel):
    account_id: int
    symbol: str = Field(..., min_length=1, max_length=16)
    trade_date: date
    side: Literal["buy", "sell"]
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fee: float = Field(0.0, ge=0)
    tax: float = Field(0.0, ge=0)
    market: Optional[Literal["cn", "hk", "us"]] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    trade_uid: Optional[str] = Field(None, max_length=128)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCashLedgerCreateRequest(BaseModel):
    account_id: int
    event_date: date
    direction: Literal["in", "out"]
    amount: float = Field(..., gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCorporateActionCreateRequest(BaseModel):
    account_id: int
    symbol: str = Field(..., min_length=1, max_length=16)
    effective_date: date
    action_type: Literal["cash_dividend", "split_adjustment"]
    market: Optional[Literal["cn", "hk", "us"]] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    cash_dividend_per_share: Optional[float] = Field(None, ge=0)
    split_ratio: Optional[float] = Field(None, gt=0)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioEventCreatedResponse(BaseModel):
    id: int


class PortfolioDeleteResponse(BaseModel):
    deleted: int


class PortfolioTradeListItem(BaseModel):
    id: int
    account_id: int
    trade_uid: Optional[str] = None
    symbol: str
    market: str
    currency: str
    trade_date: str
    side: str
    quantity: float
    price: float
    fee: float
    tax: float
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioTradeListResponse(BaseModel):
    items: List[PortfolioTradeListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioCashLedgerListItem(BaseModel):
    id: int
    account_id: int
    event_date: str
    direction: str
    amount: float
    currency: str
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioCashLedgerListResponse(BaseModel):
    items: List[PortfolioCashLedgerListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioCorporateActionListItem(BaseModel):
    id: int
    account_id: int
    symbol: str
    market: str
    currency: str
    effective_date: str
    action_type: str
    cash_dividend_per_share: Optional[float] = None
    split_ratio: Optional[float] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioCorporateActionListResponse(BaseModel):
    items: List[PortfolioCorporateActionListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioPositionItem(BaseModel):
    symbol: str
    market: str
    currency: str
    quantity: float
    avg_cost: float
    total_cost: float
    last_price: float
    market_value_base: float
    unrealized_pnl_base: float
    unrealized_pnl_pct: Optional[float] = None
    valuation_currency: str
    price_source: str = "unknown"
    price_provider: Optional[str] = None
    price_date: Optional[str] = None
    price_stale: bool = False
    price_available: bool = True


class PortfolioAccountSnapshot(BaseModel):
    account_id: int
    account_name: str
    owner_id: Optional[str] = None
    broker: Optional[str] = None
    market: str
    base_currency: str
    as_of: str
    cost_method: str
    total_cash: float
    total_market_value: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    fee_total: float
    tax_total: float
    fx_stale: bool
    positions: List[PortfolioPositionItem] = Field(default_factory=list)


class PortfolioSnapshotResponse(BaseModel):
    as_of: str
    cost_method: str
    currency: str
    account_count: int
    total_cash: float
    total_market_value: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    fee_total: float
    tax_total: float
    fx_stale: bool
    accounts: List[PortfolioAccountSnapshot] = Field(default_factory=list)


class PortfolioImportTradeItem(BaseModel):
    trade_date: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    fee: float
    tax: float
    trade_uid: Optional[str] = None
    dedup_hash: str
    currency: Optional[str] = None


class PortfolioImportParseResponse(BaseModel):
    broker: str
    record_count: int
    skipped_count: int
    error_count: int
    records: List[PortfolioImportTradeItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class PortfolioImportCommitResponse(BaseModel):
    account_id: int
    record_count: int
    inserted_count: int
    duplicate_count: int
    failed_count: int
    dry_run: bool
    errors: List[str] = Field(default_factory=list)


class PortfolioImportBrokerItem(BaseModel):
    broker: str
    aliases: List[str] = Field(default_factory=list)
    display_name: Optional[str] = None


class PortfolioImportBrokerListResponse(BaseModel):
    brokers: List[PortfolioImportBrokerItem] = Field(default_factory=list)


class PortfolioFxRefreshResponse(BaseModel):
    as_of: str
    account_count: int
    refresh_enabled: bool
    disabled_reason: Optional[str] = None
    pair_count: int
    updated_count: int
    stale_count: int
    error_count: int


class PortfolioRiskResponse(BaseModel):
    as_of: str
    account_id: Optional[int] = None
    cost_method: str
    currency: str
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    concentration: Dict[str, Any] = Field(default_factory=dict)
    sector_concentration: Dict[str, Any] = Field(default_factory=dict)
    drawdown: Dict[str, Any] = Field(default_factory=dict)
    stop_loss: Dict[str, Any] = Field(default_factory=dict)


class AllocationTargetCreateRequest(BaseModel):
    account_id: Optional[int] = None
    symbol: Optional[str] = Field(None, max_length=16)
    sector: Optional[str] = Field(None, max_length=32)
    target_pct: float = Field(..., gt=0, le=100)
    drift_threshold_pct: float = Field(2.0, gt=0, le=100)
    priority: int = Field(0, ge=0)


class AllocationTargetUpdateRequest(BaseModel):
    target_pct: Optional[float] = Field(None, gt=0, le=100)
    drift_threshold_pct: Optional[float] = Field(None, gt=0, le=100)
    priority: Optional[int] = Field(None, ge=0)


class AllocationTargetItem(BaseModel):
    id: int
    account_id: Optional[int] = None
    symbol: Optional[str] = None
    sector: Optional[str] = None
    target_pct: float
    drift_threshold_pct: float
    priority: int
    actual_pct: Optional[float] = None
    drift_pct: Optional[float] = None
    is_alert: Optional[bool] = None


class AllocationTargetListResponse(BaseModel):
    targets: List[AllocationTargetItem] = Field(default_factory=list)


class StagedRuleCreateRequest(BaseModel):
    account_id: Optional[int] = None
    symbol: str = Field(..., min_length=1, max_length=16)
    total_target_shares: float = Field(..., gt=0)
    stage_count: int = Field(3, ge=2, le=4)
    stage_pct_1: float = Field(33.33, gt=0, le=100)
    stage_pct_2: Optional[float] = Field(None, gt=0, le=100)
    stage_pct_3: Optional[float] = Field(None, gt=0, le=100)
    stage_pct_4: Optional[float] = Field(None, gt=0, le=100)
    dip_threshold_pct_2: Optional[float] = Field(-5.0)
    dip_threshold_pct_3: Optional[float] = Field(-10.0)
    dip_threshold_pct_4: Optional[float] = Field(None)


class StagedRuleItem(BaseModel):
    id: int
    account_id: Optional[int] = None
    symbol: str
    total_target_shares: float
    stage_count: int
    stage_pct_1: float
    stage_pct_2: Optional[float] = None
    stage_pct_3: Optional[float] = None
    stage_pct_4: Optional[float] = None
    dip_threshold_pct_2: Optional[float] = None
    dip_threshold_pct_3: Optional[float] = None
    dip_threshold_pct_4: Optional[float] = None


class StagedRuleListResponse(BaseModel):
    rules: List[StagedRuleItem] = Field(default_factory=list)


class StagedBuyStageItem(BaseModel):
    stage: int
    qty: float
    price_condition: str
    trigger_price: float


class RebalanceSuggestionItem(BaseModel):
    id: Optional[int] = None
    account_id: Optional[int] = None
    suggestion_type: str
    symbol: Optional[str] = None
    action: Literal["buy", "sell"]
    quantity: float
    estimated_price: float
    estimated_amount: float
    reason: Optional[str] = None
    allocation_before_pct: float
    allocation_after_pct: float


class StagedBuyItem(BaseModel):
    id: int
    account_id: Optional[int] = None
    symbol: str
    current_price: float
    current_shares: float
    total_target_shares: float
    remaining_to_buy: float
    stages: List[StagedBuyStageItem] = Field(default_factory=list)


class CashReserveStatus(BaseModel):
    target_pct: float
    actual_pct: float
    target_amount: float
    actual_amount: float
    shortfall_pct: float
    has_shortfall: bool


class RebalanceReportResponse(BaseModel):
    as_of: str
    account_id: Optional[int] = None
    cost_method: str
    has_targets: bool
    allocation_targets: List[AllocationTargetItem] = Field(default_factory=list)
    drift_alert_count: int
    suggestions: List[RebalanceSuggestionItem] = Field(default_factory=list)
    staged_buys: List[StagedBuyItem] = Field(default_factory=list)
    cash_reserve: CashReserveStatus
