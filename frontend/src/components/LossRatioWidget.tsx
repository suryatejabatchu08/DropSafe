/**
 * LossRatioWidget — Loss ratio stat card for the insurer dashboard.
 * Green < 0.70, Yellow 0.70–0.90, Red > 0.90
 */

interface LossRatioWidgetProps {
  lossRatio: number | null;
  loading?: boolean;
}

export default function LossRatioWidget({ lossRatio, loading }: LossRatioWidgetProps) {
  const getRatioColor = (ratio: number) => {
    if (ratio < 0.70) return { text: "text-green-700", bg: "bg-green-50", border: "border-green-200", badge: "bg-green-100 text-green-800" };
    if (ratio < 0.90) return { text: "text-yellow-700", bg: "bg-yellow-50", border: "border-yellow-200", badge: "bg-yellow-100 text-yellow-800" };
    return { text: "text-red-700", bg: "bg-red-50", border: "border-red-200", badge: "bg-red-100 text-red-800" };
  };

  if (loading) {
    return (
      <div className="bg-slate-100 p-6 rounded-lg border border-slate-200 animate-pulse">
        <div className="h-4 bg-slate-300 rounded w-24 mb-4" />
        <div className="h-8 bg-slate-300 rounded w-32" />
      </div>
    );
  }

  const ratio = lossRatio ?? 0;
  const pct = Math.round(ratio * 100);
  const colors = getRatioColor(ratio);
  const label = ratio < 0.70 ? "Healthy" : ratio < 0.90 ? "Watch" : "High Risk";

  return (
    <div className={`p-6 rounded-lg border ${colors.border} ${colors.bg}`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-slate-600">Loss Ratio</p>
        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${colors.badge}`}>
          {label}
        </span>
      </div>
      <p className={`text-3xl font-bold ${colors.text}`}>
        {lossRatio !== null ? `${pct}%` : "—"}
      </p>
      <p className="text-xs text-slate-500 mt-2">
        Industry benchmark: 65–75%
      </p>
    </div>
  );
}
