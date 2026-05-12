# Spec: 持仓再平衡建议

**日期**: 2026-05-12
**状态**: Draft
**类型**: feature
**Author**: muzig

## 1. 背景与目标

持仓页目前只管理订单（交易记录），用户无法直观看到当前现金/仓位的整体分布，也不知道实际仓位是否偏离目标。目标是：

- 支持用户配置各标的/行业的目标仓位比例
- 支持灵活配置分批建仓规则（各批次数量、触发价位）
- 计算并展示仓位偏离告警
- 生成再平衡建议并持久化到数据库
- 提供现金储备规划视图
- 前端通过新增 Tab 展示所有再平衡相关数据

## 2. 范围

### 2.1 包含
- 新增 3 个数据库表（`PortfolioAllocationTarget`、`PortfolioStagedPositionRule`、`PortfolioRebalanceSuggestion`）
- Repository 层 CRUD 方法
- Service 层再平衡计算逻辑
- API 层新端点及 Schema
- 前端新增「再平衡」Tab，含 4 个子区块
- 新增配置项到 `.env.example`

### 2.2 不包含
- 不包含自动触发交易或下单逻辑
- 不包含基于历史回测的智能调仓建议
- 不包含与其他账号系统的同步

## 3. 验收标准

- [ ] 后端：`./scripts/ci_gate.sh` 通过，`python -m pytest -m "not network"` 通过
- [ ] 前端：`cd apps/dsa-web && npm ci && npm run lint && npm run build` 通过
- [ ] 数据库：新表 auto-create（SQLAlchemy Base.metadata.create_all）
- [ ] 偏离告警：symbol 实际配置比例偏离超过 `drift_threshold_pct` 时前端显示告警
- [ ] 再平衡建议：API 返回 `suggestions` 列表，包含买卖方向、数量、原因
- [ ] 分批建仓：前端展示各档触发条件和对应买股数量
- [ ] 现金储备：前端展示目标储备比例 vs 实际现金比例
- [ ] 配置管理：可通过 API CRUD 配置 allocation targets 和 staged rules

## 4. 方案设计

### 4.1 数据库（src/storage.py）

**PortfolioAllocationTarget** — 每账号的标的/行业目标配置
**PortfolioStagedPositionRule** — 分批建仓规则（数量、触发价位）
**PortfolioRebalanceSuggestion** — 计算生成的再平衡建议（写库）

### 4.2 Service（src/services/portfolio_risk_service.py）

新增 `get_rebalance_suggestions()` 方法：
1. `_load_allocation_targets(account_id)` — 加载 targets
2. `_compute_drift(snapshot, targets)` — 计算实际 vs 目标偏离度
3. `_generate_rebalance_trades(snapshot, drifts, total_equity)` — 生成买卖建议并写入数据库
4. `_compute_staged_buys(snapshot, staged_rules)` — 计算分批建仓方案
5. `_compute_cash_reserve_status(snapshot, target_cash_pct)` — 现金储备状态

### 4.3 API（api/v1/endpoints/portfolio.py）

新增端点：
- `POST/GET/DELETE /api/v1/portfolio/allocation-targets` — 目标配置 CRUD
- `POST/GET/DELETE /api/v1/portfolio/staged-rules` — 分批规则 CRUD
- `GET /api/v1/portfolio/rebalance` — 获取再平衡建议（计算+读库）

### 4.4 前端（apps/dsa-web/src/pages/PortfolioPage.tsx）

新增 Tab：「再平衡」，Tab panel 内分 4 个区块：
```
[仓位偏离预警] [再平衡建议]
[分批建仓建议] [现金储备规划]
```

## 5. 实现计划

- [ ] Step 1: 新增 3 个 ORM model（storage.py）
- [ ] Step 2: 新增 repo CRUD 方法（portfolio_repo.py）
- [ ] Step 3: 新增 `get_rebalance_suggestions()` service 方法（portfolio_risk_service.py）
- [ ] Step 4: 新增 Pydantic schemas（api/v1/schemas/portfolio.py）
- [ ] Step 5: 新增 API 端点（api/v1/endpoints/portfolio.py）
- [ ] Step 6: 前端 TypeScript 类型（apps/dsa-web/src/types/portfolio.ts）
- [ ] Step 7: 前端 API client（apps/dsa-web/src/api/portfolio.ts）
- [ ] Step 8: 前端新增「再平衡」Tab（PortfolioPage.tsx）
- [ ] Step 9: 更新 .env.example
- [ ] Step 10: 更新 docs/CHANGELOG.md

## 6. 影响面

- 受影响模块：后端 service / API / 前端 portfolio 页
- 受影响运行路径：本地 / Docker / GitHub Actions / API / Web
- 兼容性影响：风险端点返回结构扩展（追加字段），老前端不读取新字段则不受影响

## 7. 回滚方案

- 直接删除新增的 3 个表
- 移除新增的 API 端点和 Schema
- 回滚 frontend PortfolioPage.tsx 到无新 Tab 版本
- 移除 .env.example 新增的配置项

## 8. 测试计划

- 本地跑 `./scripts/ci_gate.sh`
- 前端 `npm run lint && npm run build`
- 手动：创建 allocation target → 调用 rebalance API → 验证写入 → 前端展示
