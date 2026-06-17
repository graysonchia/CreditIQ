import { Flag, FileWarning, Shield, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { CustomerSelect } from "../components/CustomerSelect";
import { ShapChart } from "../components/ShapChart";
import { creditIqApi, getErrorMessage } from "../services/api";
import type { PredictionResponse } from "../types/api";
import { exportCsv, percent } from "../utils/format";

export function FraudDetection() {
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [form, setForm] = useState({
    transaction_date: new Date().toISOString().slice(0, 10),
    amount_myr: 250,
    merchant_category: "online_shopping",
    transaction_type: "card",
    is_international: false,
    transaction_hour: new Date().getHours(),
    device_type: "mobile",
    location: "Kuala Lumpur"
  });
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const label = !result ? "Safe" : result.predicted_value > 0.7 ? "High Risk" : result.predicted_value > 0.3 ? "Suspicious" : "Safe";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!customerId) {
      setError("Select a customer before running fraud detection.");
      return;
    }
    setError(null);
    try {
      setResult(await creditIqApi.predictFraud({ customer_id: customerId, ...form }));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <main className="page split-page">
      <form className="panel form-panel" onSubmit={submit}>
        <h2>Fraud Detection</h2>
        <CustomerSelect value={customerId} onChange={setCustomerId} />
        <div className="form-grid single">
          <label className="field">Transaction Date<input type="date" value={form.transaction_date} onChange={(e) => setForm({ ...form, transaction_date: e.target.value })} /></label>
          <label className="field">Amount MYR<input type="number" value={form.amount_myr} onChange={(e) => setForm({ ...form, amount_myr: Number(e.target.value) })} /></label>
          <label className="field">Merchant Category<select value={form.merchant_category} onChange={(e) => setForm({ ...form, merchant_category: e.target.value })}><option>groceries</option><option>fuel</option><option>travel</option><option>electronics</option><option>online_shopping</option></select></label>
          <label className="field">Transaction Type<select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value })}><option>card</option><option>online_transfer</option><option>e_wallet</option><option>atm_withdrawal</option></select></label>
          <label className="field">Transaction Hour<input type="number" min={0} max={23} value={form.transaction_hour} onChange={(e) => setForm({ ...form, transaction_hour: Number(e.target.value) })} /></label>
          <label className="field">Device Type<select value={form.device_type} onChange={(e) => setForm({ ...form, device_type: e.target.value })}><option>mobile</option><option>desktop</option><option>pos_terminal</option><option>atm</option></select></label>
          <label className="field">Location<input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label>
          <label className="check-field"><input type="checkbox" checked={form.is_international} onChange={(e) => setForm({ ...form, is_international: e.target.checked })} />International</label>
        </div>
        {error && <div className="alert">{error}</div>}
        <button className="btn primary">Detect Fraud</button>
      </form>
      <section className="panel result-panel">
        <h2>Fraud Signal</h2>
        {result ? (
          <>
            <div className={`gauge ${label === "High Risk" ? "high" : label === "Suspicious" ? "medium" : "low"}`}>
              <strong>{percent(result.predicted_value)}</strong>
              <span>{label}</span>
              <small>Confidence {percent(result.confidence_score)}</small>
            </div>
            <table>
              <tbody>
                <tr><th>High amount</th><td>{form.amount_myr > 3000 ? "Yes" : "No"}</td></tr>
                <tr><th>Unusual hour</th><td>{form.transaction_hour >= 1 && form.transaction_hour <= 5 ? "Yes" : "No"}</td></tr>
                <tr><th>International</th><td>{form.is_international ? "Yes" : "No"}</td></tr>
              </tbody>
            </table>
            <ShapChart explanation={result.shap_explanation} />
            <div className="action-row">
              <button className="btn danger" onClick={() => window.confirm("Flag this transaction as fraud?")}><Flag /> Flag</button>
              <button className="btn"><ShieldCheck /> Whitelist</button>
              <button className="btn"><Shield /> Save</button>
              <button className="btn" onClick={() => exportCsv("fraud-incident.csv", [{ customer_id: customerId, fraud_score: result.predicted_value }])}><FileWarning /> Incident</button>
            </div>
          </>
        ) : <div className="empty-panel">Run a transaction check to view fraud risk and anomaly factors.</div>}
      </section>
    </main>
  );
}
