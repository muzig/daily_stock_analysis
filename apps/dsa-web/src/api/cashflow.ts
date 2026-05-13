import apiClient from './index';
import { toCamelCase } from './utils';
import type { CashFlowResult } from '../stores/cashflowStore';

export const cashflowApi = {
  async analyze(description: string): Promise<CashFlowResult> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/cashflow/analyze', {
      description,
    });
    return toCamelCase<CashFlowResult>(response.data);
  },
};