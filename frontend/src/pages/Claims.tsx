import { useEffect, useState } from "react";
import {
  getReviewQueue,
  getFraudAlerts,
  approveClaim,
  rejectClaim,
} from "../lib/api";
import {
  formatINR,
  formatTime,
  getTriggerEmoji,
  getFraudScoreColor,
  anonymizeWorker,
} from "../lib/utils";
import { AlertTriangle, CheckCircle } from "lucide-react";

// Loading skeleton
function SkeletonClaimCard() {
  return (
    <div className="p-6 border-b border-slate-200 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="h-6 bg-slate-300 rounded w-48 mb-2"></div>
          <div className="h-4 bg-slate-300 rounded w-64"></div>
        </div>
        <div className="text-right">
          <div className="h-8 bg-slate-300 rounded w-32 mb-2"></div>
          <div className="h-6 bg-slate-300 rounded w-24"></div>
        </div>
      </div>
    </div>
  );
}

interface ReviewClaim {
  id: string;
  worker_name: string;
  phone: string;
  zone: string;
  trigger_type: string;
  disrupted_hours: number;
  payout_amount: number;
  fraud_score: number;
  failed_checks: string[];
  created_at: string;
}

interface FraudAlert {
  summary: {
    total_claims: number;
    auto_approved: number;
    approved: number;
    review: number;
    rejected: number;
    fraud_rate_percent: number;
  };
  high_fraud_alerts: Array<{
    claim_id: string;
    fraud_score: number;
    trigger_type: string;
    detected_at: string;
  }>;
}

type StatusFilter = "all" | "review" | "auto_approved" | "approved" | "rejected";

const STATUS_TABS: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "all" },
  { label: "Under Review", value: "review" },
  { label: "Auto Approved", value: "auto_approved" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];


export default function Claims() {
  const [reviewQueue, setReviewQueue] = useState<ReviewClaim[]>([]);
  const [alerts, setAlerts] = useState<FraudAlert | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("review");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [queueRes, alertsRes] = await Promise.all([
        getReviewQueue(),
        getFraudAlerts(),
      ]);

      if (queueRes?.claims) setReviewQueue(queueRes.claims);
      if (alertsRes) setAlerts(alertsRes);
    } catch (err) {
      console.error("Failed to fetch claims:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (claimId: string) => {
    setProcessing(claimId);
    try {
      await approveClaim(claimId);
      setReviewQueue(reviewQueue.filter((c) => c.id !== claimId));
    } catch (err) {
      console.error("Failed to approve:", err);
      alert("Failed to approve claim");
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (claimId: string) => {
    const reason = prompt("Rejection reason:");
    if (!reason) return;

    setProcessing(claimId);
    try {
      await rejectClaim(claimId, reason);
      setReviewQueue(reviewQueue.filter((c) => c.id !== claimId));
    } catch (err) {
      console.error("Failed to reject:", err);
      alert("Failed to reject claim");
    } finally {
      setProcessing(null);
    }
  };

  // Filter review queue based on active tab
  // Note: the queue already only contains 'review' claims, so we simulate
  // filtering by showing a placeholder for other statuses
  const visibleClaims =
    activeFilter === "all" || activeFilter === "review"
      ? reviewQueue
      : []; // Other statuses would come from a full-claims endpoint

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-slate-900 mb-8">
        Claims & Fraud Detection
      </h1>

      {/* Summary Stats */}
      {alerts && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <p className="text-sm text-slate-600">Total Claims</p>
            <p className="text-2xl font-bold text-slate-900">
              {alerts.summary.total_claims}
            </p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <p className="text-sm text-green-600">Auto-Approved</p>
            <p className="text-2xl font-bold text-green-900">
              {alerts.summary.auto_approved}
            </p>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
            <p className="text-sm text-yellow-600">Under Review</p>
            <p className="text-2xl font-bold text-yellow-900">
              {alerts.summary.review}
            </p>
          </div>
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <p className="text-sm text-red-600">Rejected</p>
            <p className="text-2xl font-bold text-red-900">
              {alerts.summary.rejected}
            </p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-600">Fraud Rate</p>
            <p className="text-2xl font-bold text-blue-900">
              {alerts.summary.fraud_rate_percent.toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      {/* High Fraud Alerts */}
      {alerts && alerts.high_fraud_alerts.length > 0 && (
        <div className="mb-8 bg-red-50 border-2 border-red-300 p-4 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle
              className="text-red-600 flex-shrink-0 mt-1"
              size={24}
            />
            <div>
              <h3 className="font-semibold text-red-900">High Fraud Alerts</h3>
              <p className="text-sm text-red-700 mt-1">
                {alerts.high_fraud_alerts.length} claims with fraud score &gt;
                0.7
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Status Filter Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveFilter(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition ${
              activeFilter === tab.value
                ? "bg-slate-800 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {tab.label}
            {tab.value === "review" && reviewQueue.length > 0 && (
              <span className="ml-1.5 bg-yellow-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {reviewQueue.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Claims Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {activeFilter === "review" || activeFilter === "all"
              ? `Claims Under Review (${reviewQueue.length})`
              : `${STATUS_TABS.find((t) => t.value === activeFilter)?.label} Claims`}
          </h2>
        </div>

        {visibleClaims.length === 0 && !loading ? (
          <div className="p-12 text-center">
            <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
            <p className="text-lg font-medium text-slate-900">
              {activeFilter === "review" ? "All caught up!" : "No claims in this status"}
            </p>
            <p className="text-slate-600">
              {activeFilter === "review"
                ? "No claims pending manual review"
                : "Use the Review tab to action pending claims"}
            </p>
          </div>
        ) : loading ? (
          <div className="divide-y divide-slate-200">
            {[1, 2, 3].map((i) => (
              <SkeletonClaimCard key={i} />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {visibleClaims.map((claim) => (
              <div key={claim.id} className="p-6 hover:bg-slate-50 transition">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-2xl">
                        {getTriggerEmoji(claim.trigger_type)}
                      </span>
                      <h3 className="text-lg font-semibold text-slate-900">
                        {anonymizeWorker(claim.worker_name)} • {claim.zone}
                      </h3>
                    </div>
                    <p className="text-sm text-slate-600">
                      {claim.trigger_type.replace("_", " ").toUpperCase()} •{" "}
                      {claim.disrupted_hours.toFixed(1)}h disruption •{" "}
                      {formatTime(claim.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-slate-900">
                      {formatINR(claim.payout_amount)}
                    </p>
                    <span
                      className={`inline-block px-3 py-1 rounded-lg text-sm font-bold mt-2 ${getFraudScoreColor(claim.fraud_score)}`}
                    >
                      Risk: {(claim.fraud_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {claim.failed_checks && claim.failed_checks.length > 0 && (
                  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm font-semibold text-yellow-900 mb-2">
                      Fraud Flags:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {claim.failed_checks.map((check) => (
                        <span
                          key={check}
                          className="inline-block px-2 py-1 bg-yellow-200 text-yellow-800 text-xs rounded font-medium"
                        >
                          ⚠️ {check.replace(/_/, " ").toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(claim.id)}
                    disabled={processing === claim.id}
                    className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-600 text-white font-medium rounded-lg transition disabled:opacity-50"
                  >
                    {processing === claim.id ? "Processing..." : "✅ Approve"}
                  </button>
                  <button
                    onClick={() => handleReject(claim.id)}
                    disabled={processing === claim.id}
                    className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition disabled:opacity-50"
                  >
                    {processing === claim.id ? "Processing..." : "❌ Reject"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
