export type PredictionType = "credit_score" | "loan_default" | "fraud";

export interface PredictionSummary {
  id: number;
  prediction_type: PredictionType;
  predicted_value: number;
  predicted_label: string | null;
  confidence_score: number;
  model_version: string;
  created_at: string;
}

export interface Customer {
  id: number;
  customer_code: string;
  full_name: string;
  age: number;
  gender: string;
  marital_status: string;
  employment_status: string;
  monthly_income_myr: number;
  monthly_expenses_myr: number;
  years_employed: number;
  num_dependents: number;
  education_level: string;
  existing_loans_count: number;
  existing_loans_total_myr: number;
  bankruptcy_history: boolean;
  late_payment_count_12m: number;
  credit_utilization_pct: number;
  savings_balance_myr: number;
  is_deleted?: boolean;
  created_at: string;
  prediction_history: PredictionSummary[];
}

export interface CustomerListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Customer[];
}

export interface PredictionResponse {
  id: number;
  customer_id: number;
  prediction_type: PredictionType;
  predicted_value: number;
  predicted_label: string | null;
  confidence_score: number;
  model_version: string;
  shap_explanation: ShapExplanation | null;
  missing_features: string[];
  created_at: string;
}

export interface ShapFeature {
  feature: string;
  shap_value: number;
  direction: "positive" | "negative";
}

export interface ShapExplanation {
  model_type: string;
  expected_value: number | number[] | null;
  base_value: number | null;
  top_features: ShapFeature[];
  feature_contributions: ShapFeature[];
}

export interface ModelMetric {
  id: number;
  model_name: string;
  model_version: string;
  accuracy: number | null;
  precision_score: number | null;
  recall: number | null;
  f1_score: number | null;
  roc_auc: number | null;
  trained_at: string;
  dataset_size: number;
  notes: string | null;
  created_at: string;
}

export interface PredictionDistributionItem {
  prediction_type: PredictionType;
  month: string;
  count: number;
  avg_predicted_value: number | null;
}

export interface TopRiskCustomer {
  customer_id: number;
  customer_code: string;
  full_name: string;
  risk_type: PredictionType;
  risk_score: number;
  predicted_label: string | null;
  created_at: string;
}

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
}
