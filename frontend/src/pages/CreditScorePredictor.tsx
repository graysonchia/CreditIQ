import { Save, Printer } from "lucide-react";
import { FormEvent, useState } from "react";
import { ShapChart } from "../components/ShapChart";
import { CustomerSelect } from "../components/CustomerSelect";
import { creditIqApi, getErrorMessage } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { PredictionResponse } from "../types/api";
import { currency, percent } from "../utils/format";

const initialManual = {
  age: 35,
  gender: "female",
  marital_status: "married",
  employment_status: "employed",
  monthly_income_myr: 8000,
  monthly_expenses_myr: 4200,
  years_employed: 7,
  num_dependents: 1,
  education_level: "Bachelor",
  existing_loans_count: 1,
  existing_loans_total_myr: 80000,
  bankruptcy_history: false,
  late_payment_count_12m: 0,
  credit_utilization_pct: 35,
  savings_balance_myr: 35000
};

export function CreditScorePredictor() {
  const { getCustomer } = useAppStore();
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [manual, setManual] = useState(initialManual);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function selectCustomer(id: number | null) {
    setCustomerId(id);
    if (!id) return;
    const customer = await getCustomer(id);
    setManual({
      age: customer.age,
      gender: customer.gender,
      marital_status: customer.marital_status,
      employment_status: customer.employment_status,
      monthly_income_myr: customer.monthly_income_myr,
      monthly_expenses_myr: customer.monthly_expenses_myr,
      years_employed: customer.years_employed,
      num_dependents: customer.num_dependents,
      education_level: customer.education_level,
      existing_loans_count: customer.existing_loans_count,
      existing_loans_total_myr: customer.existing_loans_total_myr,
      bankruptcy_history: customer.bankruptcy_history,
      late_payment_count_12m: customer.late_payment_count_12m,
      credit_utilization_pct: customer.credit_utilization_pct,
      savings_balance_myr: customer.savings_balance_myr
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = customerId ? { customer_id: customerId, overrides: manual } : { customer_id: 1, overrides: manual };
      setResult(await creditIqApi.predictCreditScore(payload));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page split-page">
      <form className="panel form-panel wide" onSubmit={submit}>
        <h2>Credit Score Predictor</h2>
        <CustomerSelect value={customerId} onChange={selectCustomer} />
        <div className="form-grid">
          {Object.entries(manual).map(([key, value]) =>
            typeof value === "boolean" ? (
              <label className="check-field" key={key}>
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(event) => setManual((current) => ({ ...current, [key]: event.target.checked }))}
                />
                Bankruptcy History
              </label>
            ) : (
              <div className="field" key={key}>
                <label htmlFor={key}>{key.replace(/_/g, " ")}</label>
                <input
                  id={key}
                  required
                  type={typeof value === "number" ? "number" : "text"}
                  value={value}
                  onChange={(event) =>
                    setManual((current) => ({
                      ...current,
                      [key]: typeof value === "number" ? Number(event.target.value) : event.target.value
                    }))
                  }
                />
              </div>
            )
          )}
        </div>
        {error && <div className="alert">{error}</div>}
        <button className="btn primary" disabled={loading}>{loading ? "Predicting..." : "Predict"}</button>
      </form>

      <aside className="panel result-panel">
        <h2>Result</h2>
        {result ? (
          <>
            <div className="score-box">
              <span>Predicted Credit Score</span>
              <strong>{Math.round(result.predicted_value)}</strong>
              <small>Confidence {percent(result.confidence_score)} · Model {result.model_version}</small>
            </div>
            <progress max={1} value={result.confidence_score} aria-label="Confidence score" />
            <ShapChart explanation={result.shap_explanation} />
            <div className="action-row">
              <button className="btn"><Save /> Save Prediction</button>
              <button className="btn" onClick={() => window.print()}><Printer /> Print</button>
            </div>
          </>
        ) : (
          <div className="empty-panel">Submit a profile to view credit score, confidence, and SHAP drivers.</div>
        )}
        <small>Income preview: {currency(manual.monthly_income_myr)}</small>
      </aside>
    </main>
  );
}
