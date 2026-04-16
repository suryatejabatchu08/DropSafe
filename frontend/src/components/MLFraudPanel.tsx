/**
 * MLFraudPanel — AI Fraud Detection Layer Analysis panel.
 * Shows Layer 1, Layer 2, and combined scores for claims under review.
 * Used on the Claims page.
 */

interface FraudSummary {
  total_scored: number;
  auto_approved: number;
  review: number;
  auto_rejected: number;
  auto_approved_pct: number;
  review_pct: number;
  rejected_pct: number;
  avg_layer1_score: number | null;
  avg_layer2_score: number | null;
  avg_combined_score: number | null;
  claims_with_layer2: number;
  cluster_alerts_active: number;
  false_positive_rate_est: number | null;
}

interface MLFraudPanelProps {
  summary: FraudSummary | null;
  loading?: boolean;
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-500">{label}</span>
        <span className="font-semibold text-slate-800">{(score * 100).toFixed(1)}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(score * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function MLFraudPanel({ summary, loading }: MLFraudPanelProps) {
  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg border border-slate-200 animate-pulse">
        <div className="h-5 bg-slate-200 rounded w-48 mb-4" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-slate-100 rounded" />)}
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="bg-white p-6 rounded-lg border border-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          🤖 AI Fraud Detection — Layer Analysis
        </h2>
        <span className="text-xs bg-violet-100 text-violet-800 px-2 py-1 rounded font-medium">
          Isolation Forest v1
        </span>
      </div>

      {/* Model Performance Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-slate-50 p-3 rounded-lg text-center">
          <p className="text-xl font-bold text-slate-900">{summary.total_scored}</p>
          <p className="text-xs text-slate-500 mt-1">Total Scored</p>
        </div>
        <div className="bg-green-50 p-3 rounded-lg text-center">
          <p className="text-xl font-bold text-green-800">{summary.auto_approved}</p>
          <p className="text-xs text-green-600 mt-1">
            Auto-Approved ({summary.auto_approved_pct.toFixed(1)}%)
          </p>
        </div>
        <div className="bg-yellow-50 p-3 rounded-lg text-center">
          <p className="text-xl font-bold text-yellow-800">{summary.review}</p>
          <p className="text-xs text-yellow-600 mt-1">
            In Review ({summary.review_pct.toFixed(1)}%)
          </p>
        </div>
        <div className="bg-red-50 p-3 rounded-lg text-center">
          <p className="text-xl font-bold text-red-800">{summary.auto_rejected}</p>
          <p className="text-xs text-red-600 mt-1">
            Auto-Rejected ({summary.rejected_pct.toFixed(1)}%)
          </p>
        </div>
      </div>

      {/* Layer Score Averages */}
      <div className="space-y-4 mb-6">
        <p className="text-sm font-semibold text-slate-700">Average Scores</p>
        {summary.avg_layer1_score !== null && (
          <ScoreBar
            label="Layer 1 — Rule Engine (60% weight)"
            score={summary.avg_layer1_score}
            color="bg-blue-400"
          />
        )}
        {summary.avg_layer2_score !== null && (
          <ScoreBar
            label="Layer 2 — Isolation Forest (40% weight)"
            score={summary.avg_layer2_score}
            color="bg-violet-400"
          />
        )}
        {summary.avg_combined_score !== null && (
          <ScoreBar
            label="Combined Fraud Score"
            score={summary.avg_combined_score}
            color={
              summary.avg_combined_score < 0.40
                ? "bg-green-500"
                : summary.avg_combined_score < 0.80
                ? "bg-yellow-400"
                : "bg-red-500"
            }
          />
        )}
      </div>

      {/* Footer stats */}
      <div className="flex flex-wrap gap-4 text-sm text-slate-600 pt-4 border-t border-slate-100">
        <span>
          🔬 Layer 2 applied:{" "}
          <strong className="text-slate-900">{summary.claims_with_layer2}</strong> claims
        </span>
        {summary.cluster_alerts_active > 0 && (
          <span className="text-red-600 font-semibold">
            🚨 Cluster alerts: {summary.cluster_alerts_active}
          </span>
        )}
        {summary.false_positive_rate_est !== null && (
          <span>
            FPR (est.):{" "}
            <strong className="text-slate-900">
              {(summary.false_positive_rate_est * 100).toFixed(1)}%
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}
