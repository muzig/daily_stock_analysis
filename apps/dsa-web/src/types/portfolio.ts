export type PortfolioCostMethod = 'fifo' | 'avg';
export type PortfolioSide = 'buy' | 'sell';
export type PortfolioCashDirection = 'in' | 'out';
export type PortfolioCorporateActionType = 'cash_dividend' | 'split_adjustment';

export interface PortfolioAccountItem {
  id: number;
  ownerId?: string | null;
  name: string;
  broker?: string | null;
  market: 'cn' | 'hk' | 'us';
  baseCurrency: string;
  isActive: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface PortfolioAccountListResponse {
  accounts: PortfolioAccountItem[];
}

export interface PortfolioAccountCreateRequest {
  name: string;
  broker?: string;
  market: 'cn' | 'hk' | 'us';
  baseCurrency: string;
  ownerId?: string;
}

export interface PortfolioPositionItem {
  symbol: string;
  market: string;
  currency: string;
  quantity: number;
  avgCost: number;
  totalCost: number;
  lastPrice: number;
  marketValueBase: number;
  unrealizedPnlBase: number;
  unrealizedPnlPct?: number | null;
  valuationCurrency: string;
  priceSource?: 'realtime_quote' | 'history_close' | 'missing' | string;
  priceProvider?: string | null;
  priceDate?: string | null;
  priceStale?: boolean;
  priceAvailable?: boolean;
}

export interface PortfolioAccountSnapshot {
  accountId: number;
  accountName: string;
  ownerId?: string | null;
  broker?: string | null;
  market: string;
  baseCurrency: string;
  asOf: string;
  costMethod: PortfolioCostMethod;
  totalCash: number;
  totalMarketValue: number;
  totalEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  feeTotal: number;
  taxTotal: number;
  fxStale: boolean;
  positions: PortfolioPositionItem[];
}

export interface PortfolioSnapshotResponse {
  asOf: string;
  costMethod: PortfolioCostMethod;
  currency: string;
  accountCount: number;
  totalCash: number;
  totalMarketValue: number;
  totalEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  feeTotal: number;
  taxTotal: number;
  fxStale: boolean;
  accounts: PortfolioAccountSnapshot[];
}

export interface PortfolioConcentrationItem {
  symbol: string;
  marketValueBase: number;
  weightPct: number;
  isAlert: boolean;
}

export interface PortfolioSectorConcentrationItem {
  sector: string;
  marketValueBase: number;
  weightPct: number;
  symbolCount: number;
  isAlert: boolean;
}

export interface PortfolioDrawdownBlock {
  seriesPoints: number;
  maxDrawdownPct: number;
  currentDrawdownPct: number;
  alert: boolean;
  fxStale: boolean;
}

export interface PortfolioStopLossItem {
  accountId: number;
  symbol: string;
  avgCost: number;
  lastPrice: number;
  lossPct: number;
  nearThresholdPct: number;
  isTriggered: boolean;
}

export interface PortfolioRiskResponse {
  asOf: string;
  accountId?: number | null;
  costMethod: PortfolioCostMethod;
  currency: string;
  thresholds: Record<string, number>;
  concentration: {
    totalMarketValue: number;
    topWeightPct: number;
    alert: boolean;
    topPositions: PortfolioConcentrationItem[];
  };
  sectorConcentration: {
    totalMarketValue: number;
    topWeightPct: number;
    alert: boolean;
    topSectors: PortfolioSectorConcentrationItem[];
    coverage: Record<string, number>;
    errors: string[];
  };
  drawdown: PortfolioDrawdownBlock;
  stopLoss: {
    nearAlert: boolean;
    triggeredCount: number;
    nearCount: number;
    items: PortfolioStopLossItem[];
  };
}

export interface PortfolioTradeCreateRequest {
  accountId: number;
  symbol: string;
  tradeDate: string;
  side: PortfolioSide;
  quantity: number;
  price: number;
  fee?: number;
  tax?: number;
  market?: 'cn' | 'hk' | 'us';
  currency?: string;
  tradeUid?: string;
  note?: string;
}

export interface PortfolioCashLedgerCreateRequest {
  accountId: number;
  eventDate: string;
  direction: PortfolioCashDirection;
  amount: number;
  currency?: string;
  note?: string;
}

export interface PortfolioCorporateActionCreateRequest {
  accountId: number;
  symbol: string;
  effectiveDate: string;
  actionType: PortfolioCorporateActionType;
  market?: 'cn' | 'hk' | 'us';
  currency?: string;
  cashDividendPerShare?: number;
  splitRatio?: number;
  note?: string;
}

export interface PortfolioEventCreatedResponse {
  id: number;
}

export interface PortfolioDeleteResponse {
  deleted: number;
}

export interface PortfolioTradeListItem {
  id: number;
  accountId: number;
  tradeUid?: string | null;
  symbol: string;
  market: string;
  currency: string;
  tradeDate: string;
  side: PortfolioSide;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  note?: string | null;
  createdAt?: string | null;
}

export interface PortfolioTradeListResponse {
  items: PortfolioTradeListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PortfolioCashLedgerListItem {
  id: number;
  accountId: number;
  eventDate: string;
  direction: PortfolioCashDirection;
  amount: number;
  currency: string;
  note?: string | null;
  createdAt?: string | null;
}

export interface PortfolioCashLedgerListResponse {
  items: PortfolioCashLedgerListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PortfolioCorporateActionListItem {
  id: number;
  accountId: number;
  symbol: string;
  market: string;
  currency: string;
  effectiveDate: string;
  actionType: PortfolioCorporateActionType;
  cashDividendPerShare?: number | null;
  splitRatio?: number | null;
  note?: string | null;
  createdAt?: string | null;
}

export interface PortfolioCorporateActionListResponse {
  items: PortfolioCorporateActionListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PortfolioImportTradeItem {
  tradeDate: string;
  symbol: string;
  side: PortfolioSide;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  tradeUid?: string | null;
  dedupHash: string;
  currency?: string | null;
}

export interface PortfolioImportParseResponse {
  broker: string;
  recordCount: number;
  skippedCount: number;
  errorCount: number;
  records: PortfolioImportTradeItem[];
  errors: string[];
}

export interface PortfolioImportCommitResponse {
  accountId: number;
  recordCount: number;
  insertedCount: number;
  duplicateCount: number;
  failedCount: number;
  dryRun: boolean;
  errors: string[];
}

export interface PortfolioImportBrokerItem {
  broker: string;
  aliases: string[];
  displayName?: string;
}

export interface PortfolioImportBrokerListResponse {
  brokers: PortfolioImportBrokerItem[];
}

export interface PortfolioFxRefreshResponse {
  asOf: string;
  accountCount: number;
  refreshEnabled?: boolean;
  disabledReason?: string | null;
  pairCount: number;
  updatedCount: number;
  staleCount: number;
  errorCount: number;
}

export interface AllocationTargetItem {
  id: number;
  accountId?: number | null;
  symbol?: string | null;
  sector?: string | null;
  targetPct: number;
  driftThresholdPct: number;
  priority: number;
  actualPct?: number | null;
  driftPct?: number | null;
  isAlert?: boolean | null;
}

export interface AllocationTargetCreateRequest {
  accountId?: number | null;
  symbol?: string | null;
  sector?: string | null;
  targetPct: number;
  driftThresholdPct?: number;
  priority?: number;
}

export interface AllocationTargetUpdateRequest {
  targetPct?: number | null;
  driftThresholdPct?: number | null;
  priority?: number | null;
}

export interface AllocationTargetListResponse {
  targets: AllocationTargetItem[];
}

export interface StagedRuleItem {
  id: number;
  accountId?: number | null;
  symbol: string;
  totalTargetShares: number;
  stageCount: number;
  stagePct1: number;
  stagePct2?: number | null;
  stagePct3?: number | null;
  stagePct4?: number | null;
  dipThresholdPct2?: number | null;
  dipThresholdPct3?: number | null;
  dipThresholdPct4?: number | null;
}

export interface StagedRuleCreateRequest {
  accountId?: number | null;
  symbol: string;
  totalTargetShares: number;
  stageCount?: number;
  stagePct1?: number;
  stagePct2?: number | null;
  stagePct3?: number | null;
  stagePct4?: number | null;
  dipThresholdPct2?: number | null;
  dipThresholdPct3?: number | null;
  dipThresholdPct4?: number | null;
}

export interface StagedRuleListResponse {
  rules: StagedRuleItem[];
}

export interface StagedBuyStageItem {
  stage: number;
  qty: number;
  priceCondition: string;
  triggerPrice: number;
}

export interface RebalanceSuggestionItem {
  id?: number | null;
  accountId?: number | null;
  suggestionType: string;
  symbol?: string | null;
  action: 'buy' | 'sell';
  quantity: number;
  estimatedPrice: number;
  estimatedAmount: number;
  reason?: string | null;
  allocationBeforePct: number;
  allocationAfterPct: number;
}

export interface StagedBuyItem {
  id: number;
  accountId?: number | null;
  symbol: string;
  currentPrice: number;
  currentShares: number;
  totalTargetShares: number;
  remainingToBuy: number;
  stages: StagedBuyStageItem[];
}

export interface CashReserveStatus {
  targetPct: number;
  actualPct: number;
  targetAmount: number;
  actualAmount: number;
  shortfallPct: number;
  hasShortfall: boolean;
}

export interface RebalanceReportResponse {
  asOf: string;
  accountId?: number | null;
  costMethod: string;
  hasTargets: boolean;
  allocationTargets: AllocationTargetItem[];
  driftAlertCount: number;
  suggestions: RebalanceSuggestionItem[];
  stagedBuys: StagedBuyItem[];
  cashReserve: CashReserveStatus;
}
