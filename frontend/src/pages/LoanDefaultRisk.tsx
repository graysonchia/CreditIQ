import { Download, FileCheck, ThumbsDown, ThumbsUp } from "lucide-react";
import type { CSSProperties } from "react";
import { FormEvent, useState } from "react";
import { CustomerSelect } from "../components/CustomerSelect";
import { RiskBadge } from "../components/RiskBadge";
import { ShapChart } from "../components/ShapChart";
import { creditIqApi, getErrorMessage } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { Customer, PredictionResponse } from "../types/api";
import { currency, exportCsv, percent, riskLevel } from "../utils/format";

export function LoanDefaultRisk() {
  const { getCustomer } = useAppStore();
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [form, setForm] = useState({ loan_type: "personal", requested_amount_myr: 50000, tenure_months: 60, purpose: "debt_consolidation" });
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = result ? riskLevel(result.predicted_value) : "Low";

  async function selectCustomer(id: number | null) {
    setCustomerId(id);
    setCustomer(id ? await getCustomer(id) : null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!customerId) {
      setError("Select a customer before assessing default risk.");
      return;
    }
    setError(null);
    try {
      setResult(await creditIqApi.predictLoanDefault({ customer_id: customerId, ...form }));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <main className="page split-page">
      <section className="panel form-panel">
        <h2>Loan Default Risk</h2>
        <CustomerSelect value={customerId} onChange={selectCustomer} />
        {customer && (
          <div className="profile-snippet">
            <strong>{customer.full_name}</strong>
            <span>{currency(customer.monthly_income_myr)} income · {customer.existing_loans_count} loans</span>
          </div>
        )}
        <form className="form-grid single" onSubmit={submit}>
          <label className="field">Loan Type<select value={form.loan_type} onChange={(e) => setForm({ ...form, loan_type: e.target.value })}><option>personal</option><option>auto</option><option>mortgage</option><option>education</option><option>business</option></select></label>
          <label className="field">Requested Amount<input type="number" value={form.requested_amount_myr} onChange={(e) => setForm({ ...form, requested_amount_myr: Number(e.target.value) })} /></label>
          <label className="field">Tenure Months<input type="number" value={form.tenure_months} onChange={(e) => setForm({ ...form, tenure_months: Number(e.target.value) })} /></label>
          <label className="field">Purpose<select value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })}><option>debt_consolidation</option><option>home</option><option>vehicle</option><option>education</option><option>working_capital</option><option>medical</option></select></label>
          {error && <div className="alert">{error}</div>}
          <button className="btn primary">Assess Risk</button>
        </form>
      </section>
      <section className="panel result-panel">
        <h2>Risk Assessment</h2>
        {result ? (
          <>
            <div className={`gauge ${level.toLowerCase()}`} style={{ "--score": `${result.predicted_value * 100}%` } as CSSProperties}>
              <strong>{percent(result.predicted_value)}</strong>
              <RiskBadge level={level} />
            </div>
            <div className="recommendation">
              {level === "High" ? "Higher down payment and manual review recommended." : level === "Medium" ? "Review debt-to-income ratio before approval." : "Profile is within low-risk approval range."}
            </div>
            <ShapChart explanation={result.shap_explanation} />
            <div className="action-row">
              <button className="btn"><ThumbsUp /> Approve</button>
              <button className="btn"><ThumbsDown /> Reject</button>
              <button className="btn"><FileCheck /> Save Review</button>
              <button className="btn" onClick={() => exportCsv("loan-risk-report.csv", [{ customer_id: customerId, risk: result.predicted_value }])}><Download /> Export</button>
            </div>
          </>
        ) : <div className="empty-panel">Assess a customer loan application to view risk breakdown.</div>}
      </section>
    </main>
  );
}
