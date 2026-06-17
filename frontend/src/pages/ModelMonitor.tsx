import { Download, RotateCcw, RotateCw } from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";
import { creditIqApi, getErrorMessage } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { FeatureImportanceItem } from "../types/api";
import { compact, exportCsv, percent } from "../utils/format";

const TrendChart = memo(function TrendChart({ data }: { data: Record<string, unknown>[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="trained_at" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line dataKey="accuracy" stroke="#2563eb" />
        <Line dataKey="f1_score" stroke="#059669" />
        <Line dataKey="roc_auc" stroke="#dc2626" />
      </LineChart>
    </ResponsiveContainer>
  );
});

export function ModelMonitor() {
  const { modelMetrics, distribution, loadDashboard } = useAppStore();
  const [modelType, setModelType] = useState("credit_score");
  const [importance, setImportance] = useState<FeatureImportanceItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    creditIqApi.featureImportance(modelType).then(setImportance).catch((err) => setError(getErrorMessage(err)));
  }, [modelType]);

  const current = modelMetrics.find((metric) => metric.model_name.includes(modelType)) ?? modelMetrics[0];
  const trend = useMemo(
    () =>
      modelMetrics.map((metric) => ({
        trained_at: new Date(metric.trained_at).toLocaleDateString(),
        accuracy: metric.accuracy,
        f1_score: metric.f1_score,
        roc_auc: metric.roc_auc
      })),
    [modelMetrics]
  );

  return (
    <main className="page">
      <section className="panel">
        <div className="panel-head">
          <h2>Model Monitor</h2>
          <div className="tabs" role="tablist" aria-label="Model selection">
            {["credit_score", "default", "fraud"].map((type) => (
              <button key={type} className={modelType === type ? "tab active" : "tab"} onClick={() => setModelType(type)}>
                {type.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
        {error && <div className="alert">{error}</div>}
        <div className="metric-grid">
          <div><span>Accuracy</span><strong>{percent(current?.accuracy)}</strong></div>
          <div><span>Precision</span><strong>{percent(current?.precision_score)}</strong></div>
          <div><span>Recall</span><strong>{percent(current?.recall)}</strong></div>
          <div><span>F1</span><strong>{percent(current?.f1_score)}</strong></div>
          <div><span>ROC-AUC</span><strong>{percent(current?.roc_auc)}</strong></div>
          <div><span>Dataset</span><strong>{current ? compact(current.dataset_size) : "N/A"}</strong></div>
        </div>
      </section>

      <section className="section-grid two">
        <article className="panel">
          <h2>Performance Trend</h2>
          <TrendChart data={trend} />
        </article>
        <article className="panel">
          <h2>Prediction Distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="section-grid two">
        <article className="panel">
          <h2>Global Feature Importance</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={importance.slice(0, 12)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="feature" type="category" width={130} />
              <Tooltip />
              <Bar dataKey="importance" fill="#059669" />
            </BarChart>
          </ResponsiveContainer>
        </article>
        <article className="panel">
          <h2>Admin Actions</h2>
          <div className="action-list">
            <button className="btn"><Download /> Download Artifact</button>
            <button className="btn"><RotateCcw /> Rollback Version</button>
            <button className="btn primary"><RotateCw /> Trigger Retraining</button>
            <button className="btn" onClick={() => exportCsv("model-metrics.csv", modelMetrics as unknown as Record<string, unknown>[])}>Export Metrics</button>
          </div>
        </article>
      </section>
    </main>
  );
}
