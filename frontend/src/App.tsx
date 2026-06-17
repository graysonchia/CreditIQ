import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { CreditScorePredictor } from "./pages/CreditScorePredictor";
import { LoanDefaultRisk } from "./pages/LoanDefaultRisk";
import { FraudDetection } from "./pages/FraudDetection";
import { ModelMonitor } from "./pages/ModelMonitor";
import { Customers } from "./pages/Customers";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/predict/credit-score" element={<CreditScorePredictor />} />
        <Route path="/predict/loan-default" element={<LoanDefaultRisk />} />
        <Route path="/predict/fraud" element={<FraudDetection />} />
        <Route path="/analytics/model-monitor" element={<ModelMonitor />} />
        <Route path="/customers" element={<Customers />} />
      </Route>
    </Routes>
  );
}
