import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { authService } from "./auth";
import type {
  Customer,
  CustomerListResponse,
  FeatureImportanceItem,
  ModelMetric,
  PredictionDistributionItem,
  PredictionResponse,
  TopRiskCustomer
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000
});

api.interceptors.request.use((config) => {
  const token = authService.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as RetryConfig | undefined;
  if (!config || config._retryCount === 2) {
    return Promise.reject(error);
  }
  const retryable = !error.response || [408, 429, 500, 502, 503, 504].includes(error.response.status);
  if (!retryable) {
    return Promise.reject(error);
  }
  config._retryCount = (config._retryCount ?? 0) + 1;
  await new Promise((resolve) => window.setTimeout(resolve, 400 * config._retryCount!));
  return api(config);
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.code === "ECONNABORTED") return "The request timed out. Please try again.";
    if (!error.response) return "CreditIQ API is unavailable. Check that the backend is running.";
    return `Request failed with status ${error.response.status}.`;
  }
  return "Something went wrong. Please try again.";
}

export const creditIqApi = {
  health: () => api.get<{ status: string }>("/health").then((res) => res.data),
  customers: (limit = 25, offset = 0) =>
    api.get<CustomerListResponse>("/customers", { params: { limit, offset } }).then((res) => res.data),
  customer: (id: number) => api.get<Customer>(`/customers/${id}`).then((res) => res.data),
  createCustomer: (payload: Omit<Customer, "id" | "created_at" | "prediction_history">) =>
    api.post<Customer>("/customers", payload).then((res) => res.data),
  updateCustomer: (id: number, payload: Partial<Customer>) =>
    api.put<Customer>(`/customers/${id}`, payload).then((res) => res.data),
  modelPerformance: () => api.get<ModelMetric[]>("/analytics/model-performance").then((res) => res.data),
  predictionDistribution: () =>
    api.get<PredictionDistributionItem[]>("/analytics/prediction-distribution").then((res) => res.data),
  topRiskCustomers: () => api.get<TopRiskCustomer[]>("/analytics/top-risk-customers").then((res) => res.data),
  customerInsights: (id: number) => api.get(`/analytics/customer-insights/${id}`).then((res) => res.data),
  featureImportance: (modelType: string) =>
    api.get<FeatureImportanceItem[]>(`/analytics/feature-importance/${modelType}`).then((res) => res.data),
  predictCreditScore: (payload: Record<string, unknown>) =>
    api.post<PredictionResponse>("/predictions/credit-score", payload).then((res) => res.data),
  predictLoanDefault: (payload: Record<string, unknown>) =>
    api.post<PredictionResponse>("/predictions/loan-default", payload).then((res) => res.data),
  predictFraud: (payload: Record<string, unknown>) =>
    api.post<PredictionResponse>("/predictions/fraud", payload).then((res) => res.data)
};
