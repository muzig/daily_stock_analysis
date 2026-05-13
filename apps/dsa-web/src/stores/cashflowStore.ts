import { create } from 'zustand';
import type { ParsedApiError } from '../api/error';

export interface CashFlowSummary {
  totalAssets: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  netCashFlow: number;
  assetAllocation: { name: string; value: number; percentage: number }[];
  cashFlowByCategory: { category: string; inflow: number; outflow: number }[];
}

export interface CashFlowBreakdown {
  income: { source: string; amount: number; frequency: 'monthly' | 'yearly' | 'one-time' }[];
  expenses: { category: string; amount: number; frequency: 'monthly' | 'yearly' | 'one-time' }[];
  assets: { type: string; value: number; description: string }[];
}

export interface CashFlowResult {
  summary: CashFlowSummary;
  breakdown: CashFlowBreakdown;
  insights: string[];
}

interface CashFlowState {
  isLoading: boolean;
  result: CashFlowResult | null;
  error: ParsedApiError | null;
  description: string;
  setDescription: (description: string) => void;
  setLoading: (loading: boolean) => void;
  setResult: (result: CashFlowResult | null) => void;
  setError: (error: ParsedApiError | null) => void;
  reset: () => void;
}

export const useCashFlowStore = create<CashFlowState>((set) => ({
  isLoading: false,
  result: null,
  error: null,
  description: '',

  setDescription: (description) => set({ description }),

  setLoading: (isLoading) => set({ isLoading, error: null }),

  setResult: (result) =>
    set({
      result,
      error: null,
      isLoading: false,
    }),

  setError: (error) =>
    set({
      error,
      isLoading: false,
    }),

  reset: () =>
    set({
      isLoading: false,
      result: null,
      error: null,
      description: '',
    }),
}));