import { Download, Edit, FileText, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { RiskBadge } from "../components/RiskBadge";
import { useAppStore } from "../store/appStore";
import type { Customer } from "../types/api";
import { currency, exportCsv, riskLevel } from "../utils/format";

export function Customers() {
  const { customers, totalCustomers, loadCustomers } = useAppStore();
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("All");
  const [employment, setEmployment] = useState("All");
  const [pageSize, setPageSize] = useState(25);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [checked, setChecked] = useState<number[]>([]);

  useEffect(() => {
    loadCustomers(pageSize, offset);
  }, [loadCustomers, pageSize, offset]);

  const filtered = useMemo(() => {
    return customers.filter((customer) => {
      const lastRisk = customer.prediction_history.find((item) => item.prediction_type === "loan_default")?.predicted_value ?? 0.1;
      const level = riskLevel(lastRisk);
      const matchesQuery = [customer.full_name, customer.customer_code, String(customer.id)].some((value) =>
        value.toLowerCase().includes(query.toLowerCase())
      );
      return matchesQuery && (risk === "All" || risk === level) && (employment === "All" || employment === customer.employment_status);
    });
  }, [customers, employment, query, risk]);

  return (
    <main className="page">
      <section className="panel">
        <div className="panel-head">
          <h2>Customers</h2>
          <div className="action-row">
            <button className="btn"><RefreshCw /> Re-run Predictions</button>
            <button className="btn" onClick={() => exportCsv("customers.csv", filtered as unknown as Record<string, unknown>[])}><Download /> Export</button>
          </div>
        </div>
        <div className="filter-bar">
          <input aria-label="Search customers" placeholder="Search name, ID, code" value={query} onChange={(event) => setQuery(event.target.value)} />
          <select aria-label="Risk filter" value={risk} onChange={(event) => setRisk(event.target.value)}>
            <option>All</option><option>Low</option><option>Medium</option><option>High</option>
          </select>
          <select aria-label="Employment filter" value={employment} onChange={(event) => setEmployment(event.target.value)}>
            <option>All</option><option>employed</option><option>self_employed</option><option>contract</option><option>unemployed</option><option>retired</option>
          </select>
          <select aria-label="Rows per page" value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
            <option value={10}>10</option><option value={25}>25</option><option value={50}>50</option>
          </select>
        </div>
        <table>
          <thead>
            <tr><th><span className="sr-only">Select</span></th><th>ID</th><th>Name</th><th>Age</th><th>Income</th><th>Employment</th><th>Risk</th><th>Last Prediction</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {filtered.map((customer) => {
              const lastRisk = customer.prediction_history.find((item) => item.prediction_type === "loan_default")?.predicted_value ?? 0.1;
              const level = riskLevel(lastRisk);
              return (
                <tr key={customer.id} onClick={() => setSelected(customer)} tabIndex={0}>
                  <td><input type="checkbox" checked={checked.includes(customer.id)} onChange={(event) => {
                    event.stopPropagation();
                    setChecked((current) => event.target.checked ? [...current, customer.id] : current.filter((id) => id !== customer.id));
                  }} /></td>
                  <td>{customer.customer_code}</td>
                  <td>{customer.full_name}</td>
                  <td>{customer.age}</td>
                  <td>{currency(customer.monthly_income_myr)}</td>
                  <td>{customer.employment_status}</td>
                  <td><RiskBadge level={level} /></td>
                  <td>{customer.prediction_history[0]?.prediction_type ?? "None"}</td>
                  <td><button className="icon-btn" aria-label="Edit profile"><Edit /></button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="pagination">
          <button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button>
          <span>{offset + 1}-{Math.min(offset + pageSize, totalCustomers)} of {totalCustomers}</span>
          <button className="btn" disabled={offset + pageSize >= totalCustomers} onClick={() => setOffset(offset + pageSize)}>Next</button>
        </div>
      </section>

      {selected && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="customer-detail-title">
          <section className="modal">
            <div className="panel-head">
              <h2 id="customer-detail-title">{selected.full_name}</h2>
              <button className="btn" onClick={() => setSelected(null)}>Close</button>
            </div>
            <div className="detail-grid">
              <span>Income <strong>{currency(selected.monthly_income_myr)}</strong></span>
              <span>Expenses <strong>{currency(selected.monthly_expenses_myr)}</strong></span>
              <span>Utilization <strong>{selected.credit_utilization_pct}%</strong></span>
              <span>Savings <strong>{currency(selected.savings_balance_myr)}</strong></span>
            </div>
            <h3>Prediction History</h3>
            <table>
              <tbody>
                {selected.prediction_history.map((prediction) => (
                  <tr key={prediction.id}><td>{prediction.prediction_type}</td><td>{prediction.predicted_value.toFixed(3)}</td><td>{new Date(prediction.created_at).toLocaleDateString()}</td></tr>
                ))}
              </tbody>
            </table>
            <div className="action-row">
              <button className="btn"><FileText /> Generate Report</button>
              <button className="btn">View Predictions</button>
              <button className="btn">Edit Profile</button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
