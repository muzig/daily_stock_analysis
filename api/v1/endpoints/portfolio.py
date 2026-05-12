# -*- coding: utf-8 -*-
"""Portfolio endpoints (P0 core account + snapshot workflow)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.portfolio import (
    AllocationTargetCreateRequest,
    AllocationTargetItem,
    AllocationTargetListResponse,
    AllocationTargetUpdateRequest,
    PortfolioAccountCreateRequest,
    PortfolioAccountItem,
    PortfolioAccountListResponse,
    PortfolioAccountUpdateRequest,
    PortfolioCashLedgerListResponse,
    PortfolioCashLedgerCreateRequest,
    PortfolioCorporateActionListResponse,
    PortfolioCorporateActionCreateRequest,
    PortfolioDeleteResponse,
    PortfolioEventCreatedResponse,
    PortfolioFxRefreshResponse,
    PortfolioImportBrokerListResponse,
    PortfolioImportCommitResponse,
    PortfolioImportParseResponse,
    PortfolioImportTradeItem,
    PortfolioRiskResponse,
    PortfolioSnapshotResponse,
    PortfolioTradeListResponse,
    PortfolioTradeCreateRequest,
    RebalanceReportResponse,
    StagedBuyItem,
    StagedRuleCreateRequest,
    StagedRuleItem,
    StagedRuleListResponse,
)
from src.services.portfolio_import_service import PortfolioImportService
from src.services.portfolio_risk_service import PortfolioRiskService
from src.services.portfolio_service import (
    PortfolioBusyError,
    PortfolioConflictError,
    PortfolioOversellError,
    PortfolioService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": "validation_error", "message": str(exc)},
    )


def _internal_error(message: str, exc: Exception) -> HTTPException:
    logger.error(f"{message}: {exc}", exc_info=True)
    return HTTPException(
        status_code=500,
        detail={"error": "internal_error", "message": f"{message}: {str(exc)}"},
    )


def _conflict_error(*, error: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"error": error, "message": message},
    )


def _serialize_import_record(item: dict) -> PortfolioImportTradeItem:
    payload = dict(item)
    trade_date = payload.get("trade_date")
    if isinstance(trade_date, date):
        payload["trade_date"] = trade_date.isoformat()
    else:
        payload["trade_date"] = str(trade_date)
    return PortfolioImportTradeItem(**payload)


@router.post(
    "/accounts",
    response_model=PortfolioAccountItem,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create portfolio account",
)
def create_account(request: PortfolioAccountCreateRequest) -> PortfolioAccountItem:
    service = PortfolioService()
    try:
        row = service.create_account(
            name=request.name,
            broker=request.broker,
            market=request.market,
            base_currency=request.base_currency,
            owner_id=request.owner_id,
        )
        return PortfolioAccountItem(**row)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create account failed", exc)


@router.get(
    "/accounts",
    response_model=PortfolioAccountListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List portfolio accounts",
)
def list_accounts(
    include_inactive: bool = Query(False, description="Whether to include inactive accounts"),
) -> PortfolioAccountListResponse:
    service = PortfolioService()
    try:
        rows = service.list_accounts(include_inactive=include_inactive)
        return PortfolioAccountListResponse(accounts=[PortfolioAccountItem(**item) for item in rows])
    except Exception as exc:
        raise _internal_error("List accounts failed", exc)


@router.put(
    "/accounts/{account_id}",
    response_model=PortfolioAccountItem,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update portfolio account",
)
def update_account(account_id: int, request: PortfolioAccountUpdateRequest) -> PortfolioAccountItem:
    service = PortfolioService()
    try:
        updated = service.update_account(
            account_id,
            name=request.name,
            broker=request.broker,
            market=request.market,
            base_currency=request.base_currency,
            owner_id=request.owner_id,
            is_active=request.is_active,
        )
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Account not found: {account_id}"},
            )
        return PortfolioAccountItem(**updated)
    except HTTPException:
        raise
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Update account failed", exc)


@router.delete(
    "/accounts/{account_id}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Deactivate portfolio account",
)
def delete_account(account_id: int):
    service = PortfolioService()
    try:
        ok = service.deactivate_account(account_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Account not found: {account_id}"},
            )
        return {"deleted": 1}
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Deactivate account failed", exc)


@router.post(
    "/trades",
    response_model=PortfolioEventCreatedResponse,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Record trade event",
)
def create_trade(request: PortfolioTradeCreateRequest) -> PortfolioEventCreatedResponse:
    service = PortfolioService()
    try:
        data = service.record_trade(
            account_id=request.account_id,
            symbol=request.symbol,
            trade_date=request.trade_date,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            fee=request.fee,
            tax=request.tax,
            market=request.market,
            currency=request.currency,
            trade_uid=request.trade_uid,
            note=request.note,
        )
        return PortfolioEventCreatedResponse(**data)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except PortfolioOversellError as exc:
        raise _conflict_error(error="portfolio_oversell", message=str(exc))
    except PortfolioConflictError as exc:
        raise _conflict_error(error="conflict", message=str(exc))
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create trade failed", exc)


@router.get(
    "/trades",
    response_model=PortfolioTradeListResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="List trade events",
)
def list_trades(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    date_from: Optional[date] = Query(None, description="Trade date from"),
    date_to: Optional[date] = Query(None, description="Trade date to"),
    symbol: Optional[str] = Query(None, description="Optional stock symbol filter"),
    side: Optional[str] = Query(None, description="Optional side filter: buy/sell"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PortfolioTradeListResponse:
    service = PortfolioService()
    try:
        data = service.list_trade_events(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            symbol=symbol,
            side=side,
            page=page,
            page_size=page_size,
        )
        return PortfolioTradeListResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("List trade events failed", exc)


@router.delete(
    "/trades/{trade_id}",
    response_model=PortfolioDeleteResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete trade event",
)
def delete_trade(trade_id: int) -> PortfolioDeleteResponse:
    service = PortfolioService()
    try:
        ok = service.delete_trade_event(trade_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Trade not found: {trade_id}"},
            )
        return PortfolioDeleteResponse(deleted=1)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Delete trade event failed", exc)


@router.post(
    "/cash-ledger",
    response_model=PortfolioEventCreatedResponse,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Record cash event",
)
def create_cash_ledger(request: PortfolioCashLedgerCreateRequest) -> PortfolioEventCreatedResponse:
    service = PortfolioService()
    try:
        data = service.record_cash_ledger(
            account_id=request.account_id,
            event_date=request.event_date,
            direction=request.direction,
            amount=request.amount,
            currency=request.currency,
            note=request.note,
        )
        return PortfolioEventCreatedResponse(**data)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create cash ledger event failed", exc)


@router.get(
    "/cash-ledger",
    response_model=PortfolioCashLedgerListResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="List cash ledger events",
)
def list_cash_ledger(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    date_from: Optional[date] = Query(None, description="Cash event date from"),
    date_to: Optional[date] = Query(None, description="Cash event date to"),
    direction: Optional[str] = Query(None, description="Optional direction filter: in/out"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PortfolioCashLedgerListResponse:
    service = PortfolioService()
    try:
        data = service.list_cash_ledger_events(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            direction=direction,
            page=page,
            page_size=page_size,
        )
        return PortfolioCashLedgerListResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("List cash ledger events failed", exc)


@router.delete(
    "/cash-ledger/{entry_id}",
    response_model=PortfolioDeleteResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete cash ledger event",
)
def delete_cash_ledger(entry_id: int) -> PortfolioDeleteResponse:
    service = PortfolioService()
    try:
        ok = service.delete_cash_ledger_event(entry_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Cash ledger entry not found: {entry_id}"},
            )
        return PortfolioDeleteResponse(deleted=1)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Delete cash ledger event failed", exc)


@router.post(
    "/corporate-actions",
    response_model=PortfolioEventCreatedResponse,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Record corporate action event",
)
def create_corporate_action(request: PortfolioCorporateActionCreateRequest) -> PortfolioEventCreatedResponse:
    service = PortfolioService()
    try:
        data = service.record_corporate_action(
            account_id=request.account_id,
            symbol=request.symbol,
            effective_date=request.effective_date,
            action_type=request.action_type,
            market=request.market,
            currency=request.currency,
            cash_dividend_per_share=request.cash_dividend_per_share,
            split_ratio=request.split_ratio,
            note=request.note,
        )
        return PortfolioEventCreatedResponse(**data)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create corporate action event failed", exc)


@router.get(
    "/corporate-actions",
    response_model=PortfolioCorporateActionListResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="List corporate action events",
)
def list_corporate_actions(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    date_from: Optional[date] = Query(None, description="Corporate action effective date from"),
    date_to: Optional[date] = Query(None, description="Corporate action effective date to"),
    symbol: Optional[str] = Query(None, description="Optional stock symbol filter"),
    action_type: Optional[str] = Query(None, description="Optional action type filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PortfolioCorporateActionListResponse:
    service = PortfolioService()
    try:
        data = service.list_corporate_action_events(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            symbol=symbol,
            action_type=action_type,
            page=page,
            page_size=page_size,
        )
        return PortfolioCorporateActionListResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("List corporate action events failed", exc)


@router.delete(
    "/corporate-actions/{action_id}",
    response_model=PortfolioDeleteResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete corporate action event",
)
def delete_corporate_action(action_id: int) -> PortfolioDeleteResponse:
    service = PortfolioService()
    try:
        ok = service.delete_corporate_action_event(action_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Corporate action not found: {action_id}"},
            )
        return PortfolioDeleteResponse(deleted=1)
    except PortfolioBusyError as exc:
        raise _conflict_error(error="portfolio_busy", message=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Delete corporate action event failed", exc)


@router.get(
    "/snapshot",
    response_model=PortfolioSnapshotResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get portfolio snapshot",
)
def get_snapshot(
    account_id: Optional[int] = Query(None, description="Optional account id, default returns all accounts"),
    as_of: Optional[date] = Query(None, description="Snapshot date, default today"),
    cost_method: str = Query("fifo", description="Cost method: fifo or avg"),
) -> PortfolioSnapshotResponse:
    service = PortfolioService()
    try:
        data = service.get_portfolio_snapshot(
            account_id=account_id,
            as_of=as_of,
            cost_method=cost_method,
        )
        return PortfolioSnapshotResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Get snapshot failed", exc)


@router.post(
    "/imports/csv/parse",
    response_model=PortfolioImportParseResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Parse broker CSV into normalized trade records",
)
def parse_csv_import(
    broker: str = Form(..., description="Broker id: huatai/citic/cmb"),
    file: UploadFile = File(...),
) -> PortfolioImportParseResponse:
    importer = PortfolioImportService()
    try:
        content = file.file.read()
        parsed = importer.parse_trade_csv(broker=broker, content=content)
        return PortfolioImportParseResponse(
            broker=parsed["broker"],
            record_count=parsed["record_count"],
            skipped_count=parsed["skipped_count"],
            error_count=parsed["error_count"],
            records=[_serialize_import_record(item) for item in parsed.get("records", [])],
            errors=list(parsed.get("errors", [])),
        )
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Parse CSV import failed", exc)


@router.get(
    "/imports/csv/brokers",
    response_model=PortfolioImportBrokerListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List supported broker CSV parsers",
)
def list_csv_brokers() -> PortfolioImportBrokerListResponse:
    importer = PortfolioImportService()
    try:
        return PortfolioImportBrokerListResponse(brokers=importer.list_supported_brokers())
    except Exception as exc:
        raise _internal_error("List CSV brokers failed", exc)


@router.post(
    "/imports/csv/commit",
    response_model=PortfolioImportCommitResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Parse and commit broker CSV with dedup",
)
def commit_csv_import(
    account_id: int = Form(...),
    broker: str = Form(..., description="Broker id: huatai/citic/cmb"),
    dry_run: bool = Form(False),
    file: UploadFile = File(...),
) -> PortfolioImportCommitResponse:
    importer = PortfolioImportService()
    try:
        content = file.file.read()
        parsed = importer.parse_trade_csv(broker=broker, content=content)
        result = importer.commit_trade_records(
            account_id=account_id,
            broker=parsed["broker"],
            records=list(parsed.get("records", [])),
            dry_run=dry_run,
        )
        return PortfolioImportCommitResponse(**result)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Commit CSV import failed", exc)


@router.post(
    "/fx/refresh",
    response_model=PortfolioFxRefreshResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Refresh FX cache online with stale fallback",
)
def refresh_fx_rates(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    as_of: Optional[date] = Query(None, description="Rate date, default today"),
) -> PortfolioFxRefreshResponse:
    service = PortfolioService()
    try:
        data = service.refresh_fx_rates(account_id=account_id, as_of=as_of)
        return PortfolioFxRefreshResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Refresh FX rates failed", exc)


@router.get(
    "/risk",
    response_model=PortfolioRiskResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get portfolio risk report",
)
def get_risk_report(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    as_of: Optional[date] = Query(None, description="Risk report date, default today"),
    cost_method: str = Query("fifo", description="Cost method: fifo or avg"),
) -> PortfolioRiskResponse:
    service = PortfolioRiskService()
    try:
        data = service.get_risk_report(account_id=account_id, as_of=as_of, cost_method=cost_method)
        return PortfolioRiskResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Get risk report failed", exc)


# --- Rebalance endpoints ---


@router.get(
    "/rebalance",
    response_model=RebalanceReportResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get rebalancing suggestions",
)
def get_rebalance_report(
    account_id: Optional[int] = Query(None, description="Optional account id"),
    as_of: Optional[date] = Query(None, description="Report date, default today"),
    cost_method: str = Query("fifo", description="Cost method: fifo or avg"),
) -> RebalanceReportResponse:
    service = PortfolioRiskService()
    try:
        data = service.get_rebalance_suggestions(account_id=account_id, as_of=as_of, cost_method=cost_method)
        return RebalanceReportResponse(**data)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Get rebalance report failed", exc)


@router.post(
    "/allocation-targets",
    response_model=AllocationTargetItem,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create allocation target",
)
def create_allocation_target(req: AllocationTargetCreateRequest) -> AllocationTargetItem:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        row = repo.create_allocation_target(
            account_id=req.account_id,
            symbol=req.symbol,
            sector=req.sector,
            target_pct=req.target_pct,
            drift_threshold_pct=req.drift_threshold_pct,
            priority=req.priority,
        )
        return AllocationTargetItem(
            id=row.id,
            account_id=row.account_id,
            symbol=row.symbol,
            sector=row.sector,
            target_pct=row.target_pct,
            drift_threshold_pct=row.drift_threshold_pct,
            priority=row.priority,
        )
    except Exception as exc:
        raise _internal_error("Create allocation target failed", exc)


@router.get(
    "/allocation-targets",
    response_model=AllocationTargetListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List allocation targets",
)
def list_allocation_targets(
    account_id: Optional[int] = Query(None, description="Filter by account"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
) -> AllocationTargetListResponse:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        rows = repo.get_allocation_targets(account_id=account_id, symbol=symbol, sector=sector)
        items = [
            AllocationTargetItem(
                id=r.id,
                account_id=r.account_id,
                symbol=r.symbol,
                sector=r.sector,
                target_pct=r.target_pct,
                drift_threshold_pct=r.drift_threshold_pct,
                priority=r.priority,
            )
            for r in rows
        ]
        return AllocationTargetListResponse(targets=items)
    except Exception as exc:
        raise _internal_error("List allocation targets failed", exc)


@router.put(
    "/allocation-targets/{target_id}",
    response_model=AllocationTargetItem,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Update allocation target",
)
def update_allocation_target(target_id: int, req: AllocationTargetUpdateRequest) -> AllocationTargetItem:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        row = repo.update_allocation_target(
            target_id=target_id,
            target_pct=req.target_pct,
            drift_threshold_pct=req.drift_threshold_pct,
            priority=req.priority,
        )
        if row is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Target not found"})
        return AllocationTargetItem(
            id=row.id,
            account_id=row.account_id,
            symbol=row.symbol,
            sector=row.sector,
            target_pct=row.target_pct,
            drift_threshold_pct=row.drift_threshold_pct,
            priority=row.priority,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Update allocation target failed", exc)


@router.delete(
    "/allocation-targets/{target_id}",
    response_model=PortfolioDeleteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete allocation target",
)
def delete_allocation_target(target_id: int) -> PortfolioDeleteResponse:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        ok = repo.delete_allocation_target(target_id)
        if not ok:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Target not found"})
        return PortfolioDeleteResponse(success=True, message="Deleted")
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Delete allocation target failed", exc)


@router.post(
    "/staged-rules",
    response_model=StagedRuleItem,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Create staged position rule",
)
def create_staged_rule(req: StagedRuleCreateRequest) -> StagedRuleItem:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        row = repo.create_staged_rule(
            account_id=req.account_id,
            symbol=req.symbol,
            total_target_shares=req.total_target_shares,
            stage_count=req.stage_count,
            stage_pct_1=req.stage_pct_1,
            stage_pct_2=req.stage_pct_2,
            stage_pct_3=req.stage_pct_3,
            stage_pct_4=req.stage_pct_4,
            dip_threshold_pct_2=req.dip_threshold_pct_2,
            dip_threshold_pct_3=req.dip_threshold_pct_3,
            dip_threshold_pct_4=req.dip_threshold_pct_4,
        )
        return StagedRuleItem(
            id=row.id,
            account_id=row.account_id,
            symbol=row.symbol,
            total_target_shares=row.total_target_shares,
            stage_count=row.stage_count,
            stage_pct_1=row.stage_pct_1,
            stage_pct_2=row.stage_pct_2,
            stage_pct_3=row.stage_pct_3,
            stage_pct_4=row.stage_pct_4,
            dip_threshold_pct_2=row.dip_threshold_pct_2,
            dip_threshold_pct_3=row.dip_threshold_pct_3,
            dip_threshold_pct_4=row.dip_threshold_pct_4,
        )
    except Exception as exc:
        raise _internal_error("Create staged rule failed", exc)


@router.get(
    "/staged-rules",
    response_model=StagedRuleListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List staged position rules",
)
def list_staged_rules(
    account_id: Optional[int] = Query(None, description="Filter by account"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
) -> StagedRuleListResponse:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        rows = repo.get_staged_rules(account_id=account_id, symbol=symbol)
        items = [
            StagedRuleItem(
                id=r.id,
                account_id=r.account_id,
                symbol=r.symbol,
                total_target_shares=r.total_target_shares,
                stage_count=r.stage_count,
                stage_pct_1=r.stage_pct_1,
                stage_pct_2=r.stage_pct_2,
                stage_pct_3=r.stage_pct_3,
                stage_pct_4=r.stage_pct_4,
                dip_threshold_pct_2=r.dip_threshold_pct_2,
                dip_threshold_pct_3=r.dip_threshold_pct_3,
                dip_threshold_pct_4=r.dip_threshold_pct_4,
            )
            for r in rows
        ]
        return StagedRuleListResponse(rules=items)
    except Exception as exc:
        raise _internal_error("List staged rules failed", exc)


@router.delete(
    "/staged-rules/{rule_id}",
    response_model=PortfolioDeleteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete staged position rule",
)
def delete_staged_rule(rule_id: int) -> PortfolioDeleteResponse:
    from src.repositories.portfolio_repo import PortfolioRepository
    repo = PortfolioRepository()
    try:
        ok = repo.delete_staged_rule(rule_id)
        if not ok:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Rule not found"})
        return PortfolioDeleteResponse(success=True, message="Deleted")
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Delete staged rule failed", exc)
