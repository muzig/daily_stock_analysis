import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { motion } from 'motion/react';
import {
  Pie, PieChart, ResponsiveContainer, Tooltip, Legend, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import {
  Wallet, TrendingUp, TrendingDown, Sparkles,
  DollarSign, ArrowUpRight, ArrowDownRight, Lightbulb,
  RefreshCw, ChevronDown, ChevronUp,
} from 'lucide-react';
import { cashflowApi } from '../api/cashflow';
import { getParsedApiError } from '../api/error';
import { useCashFlowStore } from '../stores/cashflowStore';
import { cn } from '../utils/cn';

const PIE_COLORS = [
  'hsl(190, 100%, 50%)',
  'hsl(247, 84%, 72%)',
  'hsl(152, 69%, 40%)',
  'hsl(37, 92%, 50%)',
  'hsl(349, 82%, 56%)',
  'hsl(200, 80%, 60%)',
];

const EXAMPLE_PROMPTS = [
  '月薪 25000，房租 6000，餐饮 3000，交通 500，基金定投 2000，持有 50 万市值的股票和 20 万存款',
  '自由职业者，月收入波动约 3-5 万，有房贷 5000/月，孩子教育 3000，无其他负债',
  '家庭年收入 80 万，房产 2 套（自住 + 出租），车贷 3000/月，日常开销约 1.5 万/月',
];

function formatMoney(value: number, currency = '¥'): string {
  if (value == null || Number.isNaN(value)) return '--';
  const abs = Math.abs(value);
  const formatted = abs >= 10000
    ? `${currency}${(abs / 10000).toFixed(2)}万`
    : `${currency}${abs.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
  return value < 0 ? `-${formatted}` : formatted;
}

function formatPercent(value: number): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `${value.toFixed(1)}%`;
}

const INPUT_CLASS =cn(
  'input-surface input-focus-glow w-full rounded-xl border px-4 py-3 text-sm',
  'transition-all focus:outline-none resize-none'
);

function KpiCard({
  label,
  value,
  subValue,
  trend,
  icon: Icon,
  delay,
}: {
  label: string;
  value: string;
  subValue?: string;
  trend?: number;
  icon: React.ComponentType<{ className?: string }>;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4 backdrop-blur-md"
      style={{
        background: 'linear-gradient(135deg, hsl(var(--card) / 0.6) 0%, hsl(var(--background) / 0.4) 100%)',
      }}
    >
      <div className="absolute inset-0 rounded-2xl border border-white/[0.06]" />
      <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-gradient-to-br from-cyan-500/[0.06] to-transparent blur-2xl" />
      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-medium uppercase tracking-widest text-secondary-text">
            {label}
          </span>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/[0.05] border border-white/[0.08]">
            <Icon className="h-4 w-4 text-cyan" />
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xl font-semibold tracking-tight text-foreground">
            {value}
          </p>
          {subValue && (
            <p className={cn(
              'text-xs font-medium',
              trend !== undefined
                ? (trend >= 0 ? 'text-success' : 'text-danger')
                : 'text-secondary-text'
            )}>
              {trend !== undefined && (
                <span className="mr-1">
                  {trend >= 0 ? <ArrowUpRight className="inline h-3 w-3" /> : <ArrowDownRight className="inline h-3 w-3" />}
                </span>
              )}
              {subValue}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function GlassCard({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        'relative overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.03]',
        'backdrop-blur-md',
        className
      )}
    >
      <div className="absolute inset-0 rounded-2xl border border-white/[0.05]" />
      <div className="relative p-5">
        <div className="absolute top-0 right-0 w-40 h-40 rounded-full bg-gradient-to-br from-cyan-500/[0.04] to-transparent blur-2xl" />
        {children}
      </div>
    </motion.div>
  );
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-secondary-text">{subtitle}</p>}
    </div>
  );
}

function BreakdownRow({
  label,
  amount,
  percentage,
  barColor,
  isIncome,
}: {
  label: string;
  amount: number;
  percentage: number;
  barColor: string;
  isIncome: boolean;
}) {
  return (
    <div className="py-2">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-secondary-text">{label}</span>
        <span className={cn(
          'text-xs font-mono font-medium',
          isIncome ? 'text-success' : 'text-danger'
        )}>
          {isIncome ? '+' : '-'}{formatMoney(amount)}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(percentage, 100)}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            className="h-full rounded-full"
            style={{ background: barColor }}
          />
        </div>
        <span className="text-[10px] font-mono text-muted-text w-10 text-right shrink-0">
          {formatPercent(percentage)}
        </span>
      </div>
    </div>
  );
}

function InsightCard({ text, index }: { text: string; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const preview = text.length > 80;

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, delay: 0.1 + index * 0.08, ease: 'easeOut' }}
      className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
    >
      <div className="flex items-start gap-2.5">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-cyan-500/[0.12] border border-cyan-500/20">
          <Lightbulb className="h-3 w-3 text-cyan" />
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn(
            'text-xs leading-relaxed text-secondary-text',
            !expanded && preview && 'line-clamp-2'
          )}>
            {text}
          </p>
          {preview && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="mt-1 text-[10px] text-cyan hover:text-cyan-400 transition-colors flex items-center gap-0.5"
            >
              {expanded ? (
                <>
                  收起 <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  展开 <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

const CashFlowPage: React.FC = () => {
  useEffect(() => {
    document.title = '现金流管理 - DSA';
  }, []);

  const { description, setDescription, isLoading, result, error, setLoading, setResult, setError } =
    useCashFlowStore();
  const [activePrompt, setActivePrompt] = useState<number | null>(null);

  const handleAnalyze = useCallback(async () => {
    if (!description.trim() || isLoading) return;
    setLoading(true);
    try {
      const data = await cashflowApi.analyze(description.trim());
      setResult(data);
    } catch (err) {
      setError(getParsedApiError(err));
    }
  }, [description, isLoading, setLoading, setResult, setError]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        void handleAnalyze();
      }
    },
    [handleAnalyze]
  );

  const handleExampleClick = (example: string, index: number) => {
    setDescription(example);
    setActivePrompt(index);
    setTimeout(() => setActivePrompt(null), 800);
  };

  return (
    <div className="cashflow-page min-h-screen">
      {/* Header */}
      <div className="mb-6 px-4 pt-6 md:px-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary-gradient shadow-cyan/20">
            <Wallet className="h-5 w-5 text-background" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">现金流管理</h1>
          </div>
        </div>
        <p className="text-xs text-secondary-text ml-[52px]">
          描述你的资产收入情况，AI 智能分析并可视化你的财务状况
        </p>
      </div>

      <div className="px-4 pb-8 md:px-6">
        {/* Two Column Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-5">
          {/* LEFT: AI Input Panel */}
          <div className="xl:col-span-2 space-y-4">
            {/* Input Card */}
            <GlassCard delay={0.05}>
              <SectionHeader
                title="描述你的财务状况"
                subtitle="用自然语言描述你的收入、支出、资产和负债情况"
              />
              <div className="relative">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={6}
                  placeholder="例如：月薪 20000，房租 5000，餐饮 3000，持有 30 万股票和 10 万存款，有 20 万房贷..."
                  className={INPUT_CLASS}
                  disabled={isLoading}
                />
                <div className="absolute bottom-3 right-3 flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-text">
                    {description.length > 0 ? `${description.length} 字` : ''}
                  </span>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => void handleAnalyze()}
                  disabled={!description.trim() || isLoading}
                  className={cn(
                    'btn-primary flex-1 text-sm',
                    isLoading && 'opacity-70'
                  )}
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      AI 分析
                    </>
                  )}
                </button>
                {result && (
                  <button
                    type="button"
                    onClick={() => {
                      useCashFlowStore.getState().reset();
                    }}
                    className="btn-secondary text-sm px-4"
                  >
                    重置
                  </button>
                )}
              </div>
            </GlassCard>

            {/* Example Prompts */}
            <GlassCard delay={0.1}>
              <p className="text-[11px] font-medium uppercase tracking-widest text-secondary-text mb-3">
                示例描述
              </p>
              <div className="space-y-2">
                {EXAMPLE_PROMPTS.map((example, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => handleExampleClick(example, index)}
                    className={cn(
                      'w-full text-left rounded-xl border px-3 py-2.5 text-xs transition-all',
                      activePrompt === index
                        ? 'border-cyan/40 bg-cyan/10 text-foreground'
                        : 'border-white/[0.06] bg-white/[0.02] text-secondary-text hover:border-white/[0.12] hover:bg-white/[0.05] hover:text-foreground'
                    )}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </GlassCard>

            {/* AI Response - Breakdown */}
            {result && (
              <GlassCard delay={0.15}>
                <SectionHeader title="收入来源" subtitle="按频率分类的月度收入明细" />
                <div className="space-y-1">
                  {result.breakdown.income.map((item, index) => (
                    <BreakdownRow
                      key={`income-${index}`}
                      label={item.source}
                      amount={item.amount}
                      percentage={
                        result.summary.monthlyIncome > 0
                          ? (item.amount / result.summary.monthlyIncome) * 100
                          : 0
                      }
                      barColor={PIE_COLORS[index % PIE_COLORS.length]}
                      isIncome
                    />
                  ))}
                </div>

                <div className="mt-5 mb-4">
                  <SectionHeader title="支出分类" subtitle="按频率分类的月度支出明细" />
                </div>
                <div className="space-y-1">
                  {result.breakdown.expenses.map((item, index) => (
                    <BreakdownRow
                      key={`expense-${index}`}
                      label={item.category}
                      amount={item.amount}
                      percentage={
                        result.summary.monthlyExpenses > 0
                          ? (item.amount / result.summary.monthlyExpenses) * 100
                          : 0
                      }
                      barColor={PIE_COLORS[(index + 2) % PIE_COLORS.length]}
                      isIncome={false}
                    />
                  ))}
                </div>

                <div className="mt-5 mb-4">
                  <SectionHeader title="资产明细" />
                </div>
                <div className="space-y-2">
                  {result.breakdown.assets.map((item, index) => (
                    <div
                      key={`asset-${index}`}
                      className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2"
                    >
                      <div>
                        <p className="text-xs font-medium text-foreground">{item.type}</p>
                        <p className="text-[10px] text-muted-text mt-0.5 line-clamp-1">
                          {item.description}
                        </p>
                      </div>
                      <p className="text-sm font-mono font-semibold text-foreground">
                        {formatMoney(item.value)}
                      </p>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )}
          </div>

          {/* RIGHT: Visualization Dashboard */}
          <div className="xl:col-span-3 space-y-4">
            {/* Error Alert */}
            {error && (
              <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-xs text-danger">
                <p className="font-medium">分析失败</p>
                <p className="mt-0.5 text-danger/80">{error.message}</p>
              </div>
            )}

            {/* Empty State */}
            {!result && !isLoading && (
              <GlassCard delay={0.08}>
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-white/[0.04] border border-white/[0.08]">
                    <Wallet className="h-8 w-8 text-cyan/50" />
                  </div>
                  <p className="text-sm font-medium text-foreground mb-1">开始你的财务分析</p>
                  <p className="text-xs text-secondary-text max-w-xs">
                    在左侧描述你的收入、支出和资产情况，AI 将为你生成完整的现金流分析报告
                  </p>
                </div>
              </GlassCard>
            )}

            {/* KPI Cards */}
            {result && (
              <>
                <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                  <KpiCard
                    label="总资产"
                    value={formatMoney(result.summary.totalAssets)}
                    trend={5.2}
                    icon={Wallet}
                    delay={0.1}
                  />
                  <KpiCard
                    label="月收入"
                    value={formatMoney(result.summary.monthlyIncome)}
                    subValue="较上月 +3.2%"
                    trend={3.2}
                    icon={TrendingUp}
                    delay={0.15}
                  />
                  <KpiCard
                    label="月支出"
                    value={formatMoney(result.summary.monthlyExpenses)}
                    subValue="较上月 -1.5%"
                    trend={-1.5}
                    icon={TrendingDown}
                    delay={0.2}
                  />
                  <KpiCard
                    label="净现金流"
                    value={formatMoney(result.summary.netCashFlow)}
                    subValue={result.summary.netCashFlow >= 0 ? '正向流入' : '负向流出'}
                    trend={
                      result.summary.monthlyIncome > 0
                        ? ((result.summary.netCashFlow / result.summary.monthlyIncome) * 100)
                        : 0
                    }
                    icon={DollarSign}
                    delay={0.25}
                  />
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {/* Asset Allocation Pie */}
                  <GlassCard delay={0.3}>
                    <SectionHeader
                      title="资产配置"
                      subtitle="各类资产占总资产的比例"
                    />
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={result.summary.assetAllocation}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="45%"
                            outerRadius={90}
                            innerRadius={55}
                            paddingAngle={3}
                          >
                            {result.summary.assetAllocation.map((_, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={PIE_COLORS[index % PIE_COLORS.length]}
                                stroke="transparent"
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value) => formatMoney(Number(value) || 0)}
                            contentStyle={{
                              background: 'hsl(var(--elevated))',
                              border: '1px solid hsl(var(--border) / 0.3)',
                              borderRadius: '0.75rem',
                              fontSize: '12px',
                              boxShadow: '0 8px 24px hsl(var(--background) / 0.3)',
                            }}
                          />
                          <Legend
                            formatter={(value) => (
                              <span className="text-[11px] text-secondary-text">{value}</span>
                            )}
                            iconSize={8}
                            iconType="circle"
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </GlassCard>

                  {/* Cash Flow Bar Chart */}
                  <GlassCard delay={0.35}>
                    <SectionHeader
                      title="分类现金流"
                      subtitle="各类别的收入与支出对比"
                    />
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={result.summary.cashFlowByCategory}
                          margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="hsl(var(--foreground) / 0.05)"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="category"
                            tick={{ fontSize: 10, fill: 'hsl(var(--muted-text))' }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis
                            tick={{ fontSize: 10, fill: 'hsl(var(--muted-text))' }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(v) => formatMoney(v)}
                          />
                          <Tooltip
                            formatter={(value) => formatMoney(Number(value) || 0)}
                            contentStyle={{
                              background: 'hsl(var(--elevated))',
                              border: '1px solid hsl(var(--border) / 0.3)',
                              borderRadius: '0.75rem',
                              fontSize: '12px',
                              boxShadow: '0 8px 24px hsl(var(--background) / 0.3)',
                            }}
                          />
                          <Bar dataKey="inflow" fill={PIE_COLORS[2]} radius={[4, 4, 0, 0]} maxBarSize={32} />
                          <Bar dataKey="outflow" fill={PIE_COLORS[4]} radius={[4, 4, 0, 0]} maxBarSize={32} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </GlassCard>
                </div>

                {/* AI Insights */}
                <GlassCard delay={0.4}>
                  <SectionHeader
                    title="AI 财务洞察"
                    subtitle="基于你的财务状况生成的个性化建议"
                  />
                  <div className="space-y-2">
                    {result.insights.map((text, index) => (
                      <InsightCard key={`insight-${index}`} text={text} index={index} />
                    ))}
                  </div>
                </GlassCard>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CashFlowPage;