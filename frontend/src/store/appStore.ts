import { create } from "zustand";
import { creditIqApi, getErrorMessage } from "../services/api";
import type { Customer, ModelMetric, PredictionDistributionItem, TopRiskCustomer } from "../types/api";

interface AppState {
  darkMode: boolean;
  loading: boolean;
  error: string | null;
  customers: Customer[];
  totalCustomers: number;
  modelMetrics: ModelMetric[];
  distribution: PredictionDistributionItem[];
  topRiskCustomers: TopRiskCustomer[];
  customerCache: Record<number, Customer>;
  toggleDarkMode: () => void;
  clearError: () => void;
  loadDashboard: () => Promise<void>;
  loadCustomers: (limit?: number, offset?: number) => Promise<void>;
  getCustomer: (id: number) => Promise<Customer>;
}

export const useAppStore = create<AppState>((set, get) => ({
  darkMode: localStorage.getItem("creditiq_theme") === "dark",
  loading: false,
  error: null,
  customers: [],
  totalCustomers: 0,
  modelMetrics: [],
  distribution: [],
  topRiskCustomers: [],
  customerCache: {},
  toggleDarkMode: () => {
    const next = !get().darkMode;
    localStorage.setItem("creditiq_theme", next ? "dark" : "light");
    set({ darkMode: next });
  },
  clearError: () => set({ error: null }),
  loadDashboard: async () => {
    set({ loading: true, error: null });
    try {
      const [customers, modelMetrics, distribution, topRiskCustomers] = await Promise.all([
        creditIqApi.customers(25, 0),
        creditIqApi.modelPerformance(),
        creditIqApi.predictionDistribution(),
        creditIqApi.topRiskCustomers()
      ]);
      set({
        customers: customers.items,
        totalCustomers: customers.total,
        modelMetrics,
        distribution,
        topRiskCustomers,
        customerCache: Object.fromEntries(customers.items.map((customer) => [customer.id, customer]))
      });
    } catch (error) {
      set({ error: getErrorMessage(error) });
    } finally {
      set({ loading: false });
    }
  },
  loadCustomers: async (limit = 25, offset = 0) => {
    set({ loading: true, error: null });
    try {
      const response = await creditIqApi.customers(limit, offset);
      set((state) => ({
        customers: response.items,
        totalCustomers: response.total,
        customerCache: { ...state.customerCache, ...Object.fromEntries(response.items.map((customer) => [customer.id, customer])) }
      }));
    } catch (error) {
      set({ error: getErrorMessage(error) });
    } finally {
      set({ loading: false });
    }
  },
  getCustomer: async (id: number) => {
    const cached = get().customerCache[id];
    if (cached) return cached;
    const customer = await creditIqApi.customer(id);
    set((state) => ({ customerCache: { ...state.customerCache, [id]: customer } }));
    return customer;
  }
}));
