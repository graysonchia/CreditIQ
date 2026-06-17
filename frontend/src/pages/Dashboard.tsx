import { Activity, AlertTriangle, Database, ShieldCheck, Users } from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { creditIqApi } from "../services/api";
import { useAppStore } from "../store/appStore";
import { PredictionSummary } from "../types/api";
import { compact, percent } from "../utils/format";
import { LoadingState } from "../components/LoadingState";
import { StatCard } from "../components/StatCard";

const DistributionChart = memo(function DistributionChart({ data }: { data: { month: string; count: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <Tooltip />
        <Area dataKey="count" stroke="#2563eb" fill="#93c5fd" />
      </AreaChart>
    </ResponsiveContainer>
  );
});

export function Dashboard() {
  const { loadDashboard, customers, totalCustomers, modelMetrics, distribution, topRiskCustomers, loading, error } = useAppStore();
  const [apiHealthy, setApiHealthy] = useState(false);

  useEffect(() => {
    loadDashboard();
    creditIqApi.health().then(() => setApiHealthy(true)).catch(() => setApiHealthy(false));
  }, [loadDashboard]);

  const recentPredictions = useMemo(
    () =>
      customers
        .flatMap((customer) =>
          customer.prediction_history.map((prediction) => ({ ...prediction, customer_name: customer.full_name }))
        )
        .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
        .slice(0, 10),
    [customers]
  );
  const predictions24h = recentPredictions.filter((item) => Date.now() - Date.parse(item.created_at) < 86_400_000).length;
  const defaultScores = topRiskCustomers.filter((item) => item.risk_type === "loan_default").map((item) => item.risk_score);
  const fraudScores = topRiskCustomers.filter((item) => item.risk_type === "fraud").map((item) => item.risk_score);
  const avgDefault = defaultScores.length ? defaultScores.reduce((sum, value) => sum + value, 0) / defaultScores.length : 0;
  const fraudRate = fraudScores.length ? fraudScores.filter((score) => score > 0.5).length / fraudScores.length : 0;

  if (loading && customers.length === 0) return <LoadingState />;

  return (
    <main className="page">
      {error && <div className="alert">{error}</div>}
      <section className="kpi-grid" aria-label="Key metrics">
        <StatCard label="Total Customers" value={compact(totalCustomers)} detail="Active customer profiles" icon={Users} />
        <StatCard label="Predictions 24h" value={String(predictions24h)} detail="Recent audit records" icon={Activity} />
        <StatCard label="Avg Default Risk" value={percent(avgDefault)} detail="From top-risk sample" icon={AlertTriangle} />
        <StatCard label="Fraud Detection Rate" value={percent(fraudRate)} detail="High-risk fraud share" icon={ShieldCheck} />
      </section>

      <section className="section-grid two">
        <article className="panel">
          <div className="panel-head">
            <h2>Model Performance</h2>
            <button className="btn" aria-label="Retrain models">Retrain</button>
          </div>
          <div className="model-grid">
            {modelMetrics.length === 0 && <div className="empty-panel">No model metrics recorded yet.</div>}
            {modelMetrics.slice(0, 3).map((metric) => (
              <div className="model-card" key={metric.id}>
                <strong>{metric.model_name}</strong>
                <span>Version {metric.model_version}</span>
                <dl>
                  <div><dt>Accuracy</dt><dd>{percent(metric.accuracy)}</dd></div>
                  <div><dt>Precision</dt><dd>{percent(metric.precision_score)}</dd></div>
                  <div><dt>Recall</dt><dd>{percent(metric.recall)}</dd></div>
                  <div><dt>F1</dt><dd>{percent(metric.f1_score)}</dd></div>
                  <div><dt>ROC-AUC</dt><dd>{percent(metric.roc_auc)}</dd></div>
                </dl>
                <small>Trained {new Date(metric.trained_at).toLocaleDateString()}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>System Status</h2>
          <div className="status-list">
            <span><Activity /> API {apiHealthy ? "healthy" : "unavailable"}</span>
            <span><Database /> Database {customers.length > 0 ? "connected" : "waiting"}</span>
            <span><ShieldCheck /> Models {modelMetrics.length > 0 ? "tracked" : "awaiting metrics"}</span>
          </div>
          <DistributionChart data={distribution.map((item) => ({ month: item.month, count: item.count }))} />
        </article>
      </section>

      <section className="panel">
        <h2>Recent Predictions</h2>
        <table>
          <thead>
            <tr><th>Customer</th><th>Type</th><th>Value</th><th>Confidence</th><th>Created</th></tr>
          </thead>
          <tbody>
            {recentPredictions.map((prediction: PredictionSummary & { customer_name: string }) => (
              <tr key={prediction.id} tabIndex={0}>
                <td>{prediction.customer_name}</td>
                <td>{prediction.prediction_type}</td>
                <td>{prediction.predicted_value.toFixed(3)}</td>
                <td>{percent(prediction.confidence_score)}</td>
                <td>{new Date(prediction.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
