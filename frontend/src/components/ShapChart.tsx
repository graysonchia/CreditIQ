import Plot from "react-plotly.js";
import type { ShapExplanation } from "../types/api";

export function ShapChart({ explanation }: { explanation: ShapExplanation | null }) {
  const topFeatures = explanation?.top_features ?? [];
  if (topFeatures.length === 0) {
    return <div className="empty-panel">No SHAP explanation available.</div>;
  }

  return (
    <Plot
      data={[
        {
          type: "bar",
          orientation: "h",
          y: topFeatures.map((item) => item.feature).reverse(),
          x: topFeatures.map((item) => item.shap_value).reverse(),
          marker: {
            color: topFeatures.map((item) => (item.direction === "positive" ? "#dc2626" : "#059669")).reverse()
          },
          hovertemplate: "%{y}<br>Contribution: %{x:.4f}<extra></extra>"
        }
      ]}
      layout={{
        autosize: true,
        height: 320,
        margin: { l: 130, r: 20, t: 10, b: 40 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        xaxis: { zeroline: true, title: { text: "SHAP value" } },
        yaxis: { automargin: true }
      }}
      config={{ displayModeBar: false, responsive: true }}
      className="plot"
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
}
