# -*- coding: utf-8 -*-
"""Portfolio risk service for concentration, drawdown and stop-loss proximity."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.config import Config, get_config
from src.repositories.portfolio_repo import PortfolioRepository
from src.services.portfolio_service import PortfolioService


class PortfolioRiskService:
    """Compute portfolio risk blocks on top of replayed snapshot data."""

    def __init__(
        self,
        *,
        repo: Optional[PortfolioRepository] = None,
        portfolio_service: Optional[PortfolioService] = None,
        config: Optional[Config] = None,
    ):
        self.repo = repo or PortfolioRepository()
        self.portfolio_service = portfolio_service or PortfolioService(repo=self.repo)
        self.config = config or get_config()
        self._data_manager = None
        self._data_manager_init_error = ""

    def get_risk_report(
        self,
        *,
        account_id: Optional[int] = None,
        as_of: Optional[date] = None,
        cost_method: str = "fifo",
    ) -> Dict[str, Any]:
        as_of_date = as_of or date.today()
        snapshot = self.portfolio_service.get_portfolio_snapshot(
            account_id=account_id,
            as_of=as_of_date,
            cost_method=cost_method,
        )

        thresholds = {
            "concentration_alert_pct": float(getattr(self.config, "portfolio_risk_concentration_alert_pct", 35.0)),
            "drawdown_alert_pct": float(getattr(self.config, "portfolio_risk_drawdown_alert_pct", 15.0)),
            "stop_loss_alert_pct": float(getattr(self.config, "portfolio_risk_stop_loss_alert_pct", 10.0)),
            "stop_loss_near_ratio": float(getattr(self.config, "portfolio_risk_stop_loss_near_ratio", 0.8)),
            "lookback_days": int(getattr(self.config, "portfolio_risk_lookback_days", 180)),
        }

        concentration = self._build_concentration(
            snapshot,
            thresholds["concentration_alert_pct"],
            as_of_date=as_of_date,
        )
        sector_concentration = self._build_sector_concentration(
            snapshot,
            thresholds["concentration_alert_pct"],
            as_of_date=as_of_date,
        )
        self._ensure_drawdown_snapshot_window(
            account_id=account_id,
            as_of_date=as_of_date,
            cost_method=cost_method,
            lookback_days=thresholds["lookback_days"],
        )
        drawdown = self._build_drawdown(
            account_id=account_id,
            as_of_date=as_of_date,
            cost_method=cost_method,
            threshold_pct=thresholds["drawdown_alert_pct"],
            lookback_days=thresholds["lookback_days"],
        )
        stop_loss = self._build_stop_loss(snapshot, thresholds)

        return {
            "as_of": as_of_date.isoformat(),
            "account_id": account_id,
            "cost_method": cost_method,
            "currency": snapshot["currency"],
            "thresholds": thresholds,
            "concentration": concentration,
            "sector_concentration": sector_concentration,
            "drawdown": drawdown,
            "stop_loss": stop_loss,
        }

    def _ensure_drawdown_snapshot_window(
        self,
        *,
        account_id: Optional[int],
        as_of_date: date,
        cost_method: str,
        lookback_days: int,
    ) -> None:
        if lookback_days <= 0:
            return

        start_date = self._resolve_backfill_start_date(
            account_id=account_id,
            as_of_date=as_of_date,
            lookback_days=lookback_days,
        )
        if start_date > as_of_date:
            return

        existing_rows = self.repo.list_daily_snapshots_for_risk(
            as_of=as_of_date,
            cost_method=cost_method,
            account_id=account_id,
            lookback_days=lookback_days,
        )
        if account_id is not None:
            existing_dates = {row.snapshot_date for row in existing_rows if int(row.account_id) == int(account_id)}
            current_date = start_date
            while current_date <= as_of_date:
                if current_date not in existing_dates:
                    self.portfolio_service.get_portfolio_snapshot(
                        account_id=account_id,
                        as_of=current_date,
                        cost_method=cost_method,
                    )
                    existing_dates.add(current_date)
                current_date += timedelta(days=1)
            return

        account_ids = [int(account.id) for account in self.repo.list_accounts(include_inactive=False)]
        if not account_ids:
            return
        existing_pairs = {(int(row.account_id), row.snapshot_date) for row in existing_rows}
        current_date = start_date
        while current_date <= as_of_date:
            if not all((aid, current_date) in existing_pairs for aid in account_ids):
                self.portfolio_service.get_portfolio_snapshot(
                    account_id=None,
                    as_of=current_date,
                    cost_method=cost_method,
                )
                for aid in account_ids:
                    existing_pairs.add((aid, current_date))
            current_date += timedelta(days=1)

    def _resolve_backfill_start_date(
        self,
        *,
        account_id: Optional[int],
        as_of_date: date,
        lookback_days: int,
    ) -> date:
        window_start = as_of_date - timedelta(days=lookback_days)
        if account_id is not None:
            first_activity = self.repo.get_first_activity_date(account_id=account_id, as_of=as_of_date)
            return max(window_start, first_activity or as_of_date)

        first_activity_candidates: List[date] = []
        for account in self.repo.list_accounts(include_inactive=False):
            first_activity = self.repo.get_first_activity_date(account_id=int(account.id), as_of=as_of_date)
            if first_activity is not None:
                first_activity_candidates.append(first_activity)
        if not first_activity_candidates:
            return as_of_date
        return max(window_start, min(first_activity_candidates))

    def _build_concentration(self, snapshot: Dict[str, Any], threshold_pct: float, *, as_of_date: date) -> Dict[str, Any]:
        total_mv = float(snapshot.get("total_market_value", 0.0) or 0.0)
        exposure_by_symbol: Dict[str, float] = {}
        for account in snapshot.get("accounts", []):
            for pos in account.get("positions", []):
                symbol = str(pos.get("symbol") or "").strip().upper()
                if not symbol:
                    continue
                market_value = float(pos.get("market_value_base") or 0.0)
                valuation_currency = str(pos.get("valuation_currency") or account.get("base_currency") or "CNY")
                converted, _, _ = self.portfolio_service.convert_amount(
                    amount=market_value,
                    from_currency=valuation_currency,
                    to_currency="CNY",
                    as_of_date=as_of_date,
                )
                exposure_by_symbol[symbol] = exposure_by_symbol.get(symbol, 0.0) + converted

        rows = []
        for symbol, exposure in exposure_by_symbol.items():
            weight = (exposure / total_mv * 100.0) if total_mv > 0 else 0.0
            rows.append(
                {
                    "symbol": symbol,
                    "market_value_base": round(exposure, 6),
                    "weight_pct": round(weight, 4),
                    "is_alert": bool(weight >= threshold_pct),
                }
            )
        rows.sort(key=lambda item: item["market_value_base"], reverse=True)

        top_weight = rows[0]["weight_pct"] if rows else 0.0
        return {
            "total_market_value": round(total_mv, 6),
            "top_weight_pct": round(float(top_weight), 4),
            "alert": bool(top_weight >= threshold_pct),
            "top_positions": rows[:10],
        }

    def _build_sector_concentration(
        self,
        snapshot: Dict[str, Any],
        threshold_pct: float,
        *,
        as_of_date: date,
    ) -> Dict[str, Any]:
        total_mv = float(snapshot.get("total_market_value", 0.0) or 0.0)
        sector_exposure: Dict[str, float] = {}
        sector_symbols: Dict[str, set] = {}
        coverage = {
            "classified_count": 0,
            "unclassified_count": 0,
            "failed_count": 0,
        }
        errors: List[str] = []
        board_cache: Dict[Tuple[str, str], str] = {}

        for account in snapshot.get("accounts", []):
            for pos in account.get("positions", []):
                symbol = str(pos.get("symbol") or "").strip().upper()
                market = str(pos.get("market") or account.get("market") or "").strip().lower()
                if not symbol:
                    continue

                market_value = float(pos.get("market_value_base") or 0.0)
                valuation_currency = str(pos.get("valuation_currency") or account.get("base_currency") or "CNY")
                converted, _, _ = self.portfolio_service.convert_amount(
                    amount=market_value,
                    from_currency=valuation_currency,
                    to_currency="CNY",
                    as_of_date=as_of_date,
                )

                sector = self._resolve_primary_sector(
                    symbol=symbol,
                    market=market,
                    board_cache=board_cache,
                    coverage=coverage,
                    errors=errors,
                )
                sector_exposure[sector] = sector_exposure.get(sector, 0.0) + converted
                sector_symbols.setdefault(sector, set()).add(symbol)

        rows = []
        for sector, exposure in sector_exposure.items():
            weight = (exposure / total_mv * 100.0) if total_mv > 0 else 0.0
            rows.append(
                {
                    "sector": sector,
                    "market_value_base": round(exposure, 6),
                    "weight_pct": round(weight, 4),
                    "symbol_count": len(sector_symbols.get(sector, set())),
                    "is_alert": bool(weight >= threshold_pct),
                }
            )
        rows.sort(key=lambda item: item["market_value_base"], reverse=True)
        top_weight = rows[0]["weight_pct"] if rows else 0.0

        return {
            "total_market_value": round(total_mv, 6),
            "top_weight_pct": round(float(top_weight), 4),
            "alert": bool(top_weight >= threshold_pct),
            "top_sectors": rows[:10],
            "coverage": coverage,
            "errors": errors[:20],
        }

    def _resolve_primary_sector(
        self,
        *,
        symbol: str,
        market: str,
        board_cache: Dict[Tuple[str, str], str],
        coverage: Dict[str, int],
        errors: List[str],
    ) -> str:
        cache_key = (symbol, market)
        if cache_key in board_cache:
            return board_cache[cache_key]

        if market != "cn":
            coverage["unclassified_count"] += 1
            board_cache[cache_key] = "UNCLASSIFIED"
            return board_cache[cache_key]

        try:
            boards = self._fetch_belong_boards(symbol)
            sector_name = self._pick_primary_board_name(boards)
            if sector_name:
                coverage["classified_count"] += 1
                board_cache[cache_key] = sector_name
                return board_cache[cache_key]
        except Exception as exc:
            coverage["failed_count"] += 1
            errors.append(f"{symbol}: {exc}")

        coverage["unclassified_count"] += 1
        board_cache[cache_key] = "UNCLASSIFIED"
        return board_cache[cache_key]

    def _fetch_belong_boards(self, symbol: str) -> List[Dict[str, Any]]:
        manager = self._get_data_manager()
        if manager is None:
            return []
        result = manager.get_belong_boards(symbol)
        if isinstance(result, list):
            return result
        return []

    @staticmethod
    def _pick_primary_board_name(boards: List[Dict[str, Any]]) -> Optional[str]:
        if not boards:
            return None

        preferred: Optional[str] = None
        fallback: Optional[str] = None
        for item in boards:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            if fallback is None:
                fallback = name
            type_text = str(item.get("type") or "").strip().lower()
            if "行业" in type_text or "industry" in type_text:
                preferred = name
                break
        return preferred or fallback

    def _get_data_manager(self):
        if self._data_manager is not None:
            return self._data_manager
        if self._data_manager_init_error:
            return None
        try:
            from data_provider import DataFetcherManager

            self._data_manager = DataFetcherManager()
            return self._data_manager
        except Exception as exc:  # pragma: no cover - fail-open initialization
            self._data_manager_init_error = str(exc)
            return None

    def _build_drawdown(
        self,
        *,
        account_id: Optional[int],
        as_of_date: date,
        cost_method: str,
        threshold_pct: float,
        lookback_days: int,
    ) -> Dict[str, Any]:
        rows = self.repo.list_daily_snapshots_for_risk(
            as_of=as_of_date,
            cost_method=cost_method,
            account_id=account_id,
            lookback_days=lookback_days,
        )
        if not rows:
            return {
                "series_points": 0,
                "max_drawdown_pct": 0.0,
                "current_drawdown_pct": 0.0,
                "alert": False,
                "fx_stale": False,
            }

        grouped: Dict[str, float] = {}
        stale_flag = False
        for row in rows:
            key = row.snapshot_date.isoformat()
            converted, stale, _ = self.portfolio_service.convert_amount(
                amount=float(row.total_equity or 0.0),
                from_currency=str(row.base_currency or "CNY"),
                to_currency="CNY",
                as_of_date=row.snapshot_date,
            )
            grouped[key] = grouped.get(key, 0.0) + converted
            stale_flag = stale_flag or stale or bool(row.fx_stale)

        series: List[Tuple[str, float]] = sorted(grouped.items(), key=lambda item: item[0])
        peak = 0.0
        max_drawdown = 0.0
        current_drawdown = 0.0
        for _, equity in series:
            peak = max(peak, equity)
            if peak <= 0:
                drawdown = 0.0
            else:
                drawdown = (peak - equity) / peak * 100.0
            max_drawdown = max(max_drawdown, drawdown)
            current_drawdown = drawdown

        return {
            "series_points": len(series),
            "max_drawdown_pct": round(max_drawdown, 4),
            "current_drawdown_pct": round(current_drawdown, 4),
            "alert": bool(max_drawdown >= threshold_pct),
            "fx_stale": stale_flag,
        }

    @staticmethod
    def _build_stop_loss(snapshot: Dict[str, Any], thresholds: Dict[str, Any]) -> Dict[str, Any]:
        stop_loss_pct = float(thresholds["stop_loss_alert_pct"])
        near_ratio = float(thresholds["stop_loss_near_ratio"])
        near_threshold = stop_loss_pct * near_ratio

        warnings: List[Dict[str, Any]] = []
        for account in snapshot.get("accounts", []):
            for pos in account.get("positions", []):
                avg_cost = float(pos.get("avg_cost", 0.0) or 0.0)
                last_price = float(pos.get("last_price", 0.0) or 0.0)
                if avg_cost <= 0:
                    continue
                loss_pct = max(0.0, (avg_cost - last_price) / avg_cost * 100.0)
                if loss_pct < near_threshold:
                    continue
                warnings.append(
                    {
                        "account_id": account.get("account_id"),
                        "symbol": pos.get("symbol"),
                        "avg_cost": round(avg_cost, 8),
                        "last_price": round(last_price, 8),
                        "loss_pct": round(loss_pct, 4),
                        "near_threshold_pct": round(near_threshold, 4),
                        "is_triggered": bool(loss_pct >= stop_loss_pct),
                    }
                )

        warnings.sort(key=lambda item: item["loss_pct"], reverse=True)
        return {
            "near_alert": len(warnings) > 0,
            "triggered_count": sum(1 for item in warnings if item["is_triggered"]),
            "near_count": len(warnings),
            "items": warnings[:20],
        }

    def get_rebalance_suggestions(
        self,
        *,
        account_id: Optional[int] = None,
        as_of: Optional[date] = None,
        cost_method: str = "fifo",
    ) -> Dict[str, Any]:
        as_of_date = as_of or date.today()
        snapshot = self.portfolio_service.get_portfolio_snapshot(
            account_id=account_id,
            as_of=as_of_date,
            cost_method=cost_method,
        )

        default_drift_threshold = float(getattr(self.config, "portfolio_rebalance_drift_threshold_pct", 2.0))
        default_cash_reserve_pct = float(getattr(self.config, "portfolio_rebalance_default_cash_reserve_pct", 10.0))

        accounts = snapshot.get("accounts", [])
        if account_id is not None:
            accounts = [acc for acc in accounts if acc.get("account_id") == account_id]

        all_targets: List[Dict[str, Any]] = []
        all_staged_rules: List[Any] = []
        all_suggestions: List[Dict[str, Any]] = []

        target_cash_pct = default_cash_reserve_pct
        actual_cash_pct = 0.0

        for account in accounts:
            acc_id = account.get("account_id")
            total_equity = float(account.get("total_equity", 0.0) or 0.0)
            total_cash = float(account.get("total_cash", 0.0) or 0.0)
            if total_equity > 0:
                actual_cash_pct = total_cash / total_equity * 100.0

            targets = self.repo.get_allocation_targets(account_id=acc_id)
            for t in targets:
                all_targets.append(self._build_allocation_target_item(t, account, snapshot, default_drift_threshold))

            staged_rules = self.repo.get_staged_rules(account_id=acc_id)
            all_staged_rules.extend(staged_rules)

        total_equity_all = float(snapshot.get("total_equity", 0.0) or 0.0)
        total_mv_all = float(snapshot.get("total_market_value", 0.0) or 0.0)
        total_cash_all = float(snapshot.get("total_cash", 0.0) or 0.0)

        drift_alerts = [t for t in all_targets if t.get("is_alert")]
        rebalance_suggestions = self._generate_rebalance_trades(
            snapshot=snapshot,
            targets=all_targets,
            total_equity=total_equity_all,
            as_of_date=as_of_date,
        )

        staged_buy_items = self._compute_staged_buys(snapshot=snapshot, staged_rules=all_staged_rules, as_of_date=as_of_date)

        cash_shortfall_pct = max(0.0, target_cash_pct - actual_cash_pct)
        cash_reserve = {
            "target_pct": round(target_cash_pct, 2),
            "actual_pct": round(actual_cash_pct, 2),
            "target_amount": round(target_cash_pct / 100.0 * total_equity_all, 2),
            "actual_amount": round(total_cash_all, 2),
            "shortfall_pct": round(cash_shortfall_pct, 2),
            "has_shortfall": cash_shortfall_pct > 0.1,
        }

        for sug in rebalance_suggestions:
            sug["suggestion_type"] = "rebalance"
        all_suggestions.extend(rebalance_suggestions)
        for sb in staged_buy_items:
            sb["suggestion_type"] = "staged_buy"
        all_suggestions.extend(staged_buy_items)

        if all_suggestions and account_id is not None:
            self.repo.delete_suggestions_before(account_id, as_of_date)
            self.repo.save_rebalance_suggestions(account_id, as_of_date, all_suggestions)

        return {
            "as_of": as_of_date.isoformat(),
            "account_id": account_id,
            "cost_method": cost_method,
            "has_targets": len(all_targets) > 0,
            "allocation_targets": all_targets,
            "drift_alert_count": len(drift_alerts),
            "suggestions": all_suggestions,
            "staged_buys": staged_buy_items,
            "cash_reserve": cash_reserve,
        }

    def _build_allocation_target_item(
        self,
        target: Any,
        account: Dict[str, Any],
        snapshot: Dict[str, Any],
        default_threshold: float,
    ) -> Dict[str, Any]:
        symbol = target.symbol
        sector = target.sector
        target_pct = float(target.target_pct)
        drift_threshold = float(target.drift_threshold_pct or default_threshold)

        actual_pct = 0.0
        if symbol:
            for pos in account.get("positions", []):
                if str(pos.get("symbol") or "").strip().upper() == symbol.strip().upper():
                    mv = float(pos.get("market_value_base") or 0.0)
                    total_eq = float(account.get("total_equity", 0.0) or 0.0)
                    if total_eq > 0:
                        actual_pct = mv / total_eq * 100.0
                    break
        elif sector:
            sector_mv = 0.0
            total_eq = float(account.get("total_equity", 0.0) or 0.0)
            for pos in account.get("positions", []):
                pos_sector = self._resolve_primary_sector_for_position(pos, account)
                if pos_sector == sector:
                    sector_mv += float(pos.get("market_value_base") or 0.0)
            if total_eq > 0:
                actual_pct = sector_mv / total_eq * 100.0

        drift_pct = actual_pct - target_pct
        return {
            "id": target.id,
            "account_id": target.account_id,
            "symbol": symbol,
            "sector": sector,
            "target_pct": round(target_pct, 2),
            "actual_pct": round(actual_pct, 2),
            "drift_pct": round(drift_pct, 2),
            "drift_threshold_pct": round(drift_threshold, 2),
            "is_alert": abs(drift_pct) > drift_threshold,
        }

    def _resolve_primary_sector_for_position(self, pos: Dict[str, Any], account: Dict[str, Any]) -> Optional[str]:
        symbol = str(pos.get("symbol") or "").strip().upper()
        market = str(pos.get("market") or account.get("market") or "").strip().lower()
        if not symbol or market != "cn":
            return None
        try:
            boards = self._fetch_belong_boards(symbol)
            return self._pick_primary_board_name(boards)
        except Exception:
            return None

    def _generate_rebalance_trades(
        self,
        snapshot: Dict[str, Any],
        targets: List[Dict[str, Any]],
        total_equity: float,
        as_of_date: date,
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        if total_equity <= 0:
            return suggestions

        symbol_to_position: Dict[str, Dict[str, Any]] = {}
        for account in snapshot.get("accounts", []):
            for pos in account.get("positions", []):
                sym = str(pos.get("symbol") or "").strip().upper()
                if sym:
                    symbol_to_position[sym] = pos

        for t in targets:
            sym = t.get("symbol")
            if not sym:
                continue
            target_pct = float(t.get("target_pct", 0.0))
            actual_pct = float(t.get("actual_pct", 0.0))
            drift_pct = actual_pct - target_pct
            if abs(drift_pct) <= float(t.get("drift_threshold_pct", 0.0)):
                continue

            target_value = target_pct / 100.0 * total_equity
            actual_value = actual_pct / 100.0 * total_equity
            diff_value = target_value - actual_value

            pos = symbol_to_position.get(sym, {})
            last_price = float(pos.get("last_price") or 0.0)
            if last_price <= 0:
                continue

            quantity = abs(diff_value) / last_price
            action = "buy" if diff_value > 0 else "sell"
            estimated_amount = quantity * last_price
            allocation_after = (actual_value + diff_value) / total_equity * 100.0 if total_equity > 0 else 0.0

            if abs(quantity) < 0.01:
                continue

            suggestions.append({
                "account_id": t.get("account_id"),
                "symbol": sym,
                "action": action,
                "quantity": round(quantity, 4),
                "estimated_price": round(last_price, 4),
                "estimated_amount": round(estimated_amount, 2),
                "reason": f"{'买入' if action == 'buy' else '卖出'}至目标仓位 {target_pct:.1f}%（当前偏离 {drift_pct:+.1f}%）",
                "allocation_before_pct": round(actual_pct, 2),
                "allocation_after_pct": round(allocation_after, 2),
            })

        return suggestions

    def _compute_staged_buys(
        self,
        snapshot: Dict[str, Any],
        staged_rules: List[Any],
        as_of_date: date,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        symbol_to_position: Dict[str, Dict[str, Any]] = {}
        for account in snapshot.get("accounts", []):
            for pos in account.get("positions", []):
                sym = str(pos.get("symbol") or "").strip().upper()
                if sym:
                    symbol_to_position[sym] = pos

        for rule in staged_rules:
            sym = str(rule.symbol or "").strip().upper()
            pos = symbol_to_position.get(sym, {})
            current_price = float(pos.get("last_price") or 0.0)
            current_shares = float(pos.get("quantity") or 0.0)
            total_target = float(rule.total_target_shares)

            stages = []
            remaining_to_buy = max(0.0, total_target - current_shares)

            stage_pcts = [
                (1, float(rule.stage_pct_1 or 0), None),
                (2, float(rule.stage_pct_2) if rule.stage_pct_2 else 0, float(rule.dip_threshold_pct_2) if rule.dip_threshold_pct_2 else None),
                (3, float(rule.stage_pct_3) if rule.stage_pct_3 else 0, float(rule.dip_threshold_pct_3) if rule.dip_threshold_pct_3 else None),
                (4, float(rule.stage_pct_4) if rule.stage_pct_4 else 0, float(rule.dip_threshold_pct_4) if rule.dip_threshold_pct_4 else None),
            ]

            for stage_num, stage_pct, dip_thresh in stage_pcts:
                if stage_pct <= 0:
                    continue
                qty = total_target * stage_pct / 100.0
                price_condition = "now"
                if dip_thresh is not None and stage_num > 1:
                    trigger_price = current_price * (1 + dip_thresh / 100.0)
                    price_condition = f"{dip_thresh:+.1f}% (≈{trigger_price:.2f})"
                elif stage_num > 1:
                    price_condition = f"{dip_thresh:+.1f}%" if dip_thresh else "later"

                stages.append({
                    "stage": stage_num,
                    "qty": round(qty, 4),
                    "price_condition": price_condition,
                    "trigger_price": round(current_price * (1 + dip_thresh / 100.0), 4) if dip_thresh and stage_num > 1 else round(current_price, 4),
                })

            items.append({
                "id": rule.id,
                "account_id": rule.account_id,
                "symbol": sym,
                "current_price": round(current_price, 4),
                "current_shares": round(current_shares, 4),
                "total_target_shares": round(total_target, 4),
                "remaining_to_buy": round(remaining_to_buy, 4),
                "stages": stages,
            })

        return items
