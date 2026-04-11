import { useEffect, useState } from "react";
import { getPayoutSummary, retryPayout } from "../lib/api";
import { formatINR, formatTime } from "../lib/utils";
import { AlertTriangle, RefreshCw } from "lucide-react";

// Loading skeleton
function SkeletonStatCard() {
  return (
    <div className="bg-slate-100 p-6 rounded-lg border border-slate-200 animate-pulse">
      <div className="h-4 bg-slate-300 rounded w-20 mb-4"></div>
      <div className="h-10 bg-slate-300 rounded w-32"></div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-200 animate-pulse">
      <td className="px-4 py-3"><div className="h-4 bg-slate-200 rounded w-24"></div></td>
      <td className="px-4 py-3"><div className="h-4 bg-slate-200 rounded w-20"></div></td>
      <td className="px-4 py-3"><div className="h-4 bg-slate-200 rounded w-16"></div></td>
      <td className="px-4 py-3"><div className="h-6 bg-slate-200 rounded w-20"></div></td>
      <td className="px-4 py-3"><div className="h-8 bg-slate-200 rounded w-16"></div></td>
    </tr>
  );
}

interface PayoutSummary {
  today: { total: number; successful: number; count: number };
  week: { total: number; successful: number; count: number };
  pending: number;
  failed: number;
  success_rate: number;
  recent_payouts?: RecentPayout[];
}

interface RecentPayout {
  payout_id: string;
  razorpay_ref: string;
  amount: number;
  status: string;
  trigger_type?: string;
  paid_at?: string;
  worker_name?: string;
}

const STATUS_BADGE: Record<string, string> = {
  success: "bg-green-100 text-green-800",
  initiated: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  reversed: "bg-orange-100 text-orange-800",
  queued: "bg-slate-100 text-slate-800",
};

export default function Payouts() {
  const [summary, setSummary] = useState<PayoutSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const data = await getPayoutSummary();
      if (data) setSummary(data);
    } catch (err) {
      console.error("Failed to fetch payouts:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (razorpayRef: string) => {
    setRetrying(razorpayRef);
    try {
      const result = await retryPayout(razorpayRef);
      if (result?.status === "retrying") {
        alert(`✅ Retry initiated! New payout: ${result.payout_id}`);
        fetchData(); // Refresh
      } else {
        alert(`❌ Retry failed: ${result?.message || "Unknown error"}`);
      }
    } catch (err) {
      alert("Failed to retry payout");
    } finally {
      setRetrying(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-4xl font-bold text-slate-900 mb-8">Payouts</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SkeletonStatCard />
          <SkeletonStatCard />
          <SkeletonStatCard />
        </div>
      </div>
    );
  }

  const recentPayouts = summary?.recent_payouts ?? [];

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-slate-900 mb-8">Payouts</h1>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Today */}
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-600 font-medium">Today</p>
          <p className="text-3xl font-bold text-blue-900 mt-2">
            {formatINR(summary?.today.total || 0)}
          </p>
          <p className="text-sm text-blue-600 mt-1">
            {summary?.today.successful || 0} of {summary?.today.count || 0}{" "}
            successful
          </p>
        </div>

        {/* This Week */}
        <div className="bg-green-50 p-6 rounded-lg border border-green-200">
          <p className="text-sm text-green-600 font-medium">This Week</p>
          <p className="text-3xl font-bold text-green-900 mt-2">
            {formatINR(summary?.week.total || 0)}
          </p>
          <p className="text-sm text-green-600 mt-1">
            {summary?.week.successful || 0} of {summary?.week.count || 0}{" "}
            successful
          </p>
        </div>

        {/* Success Rate */}
        <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
          <p className="text-sm text-slate-600 font-medium">Success Rate</p>
          <p className="text-3xl font-bold text-slate-900 mt-2">
            {summary?.success_rate.toFixed(1)}%
          </p>
          <div className="mt-3 h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500"
              style={{ width: `${summary?.success_rate || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Pending & Failed */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-yellow-600 flex-shrink-0 mt-1" size={24} />
            <div>
              <p className="text-sm font-semibold text-yellow-900">Pending Payouts</p>
              <p className="text-3xl font-bold text-yellow-900 mt-1">{summary?.pending || 0}</p>
              <p className="text-sm text-yellow-700 mt-1">Will be processed soon</p>
            </div>
          </div>
        </div>
        <div className="bg-red-50 p-6 rounded-lg border border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-red-600 flex-shrink-0 mt-1" size={24} />
            <div>
              <p className="text-sm font-semibold text-red-900">Failed Payouts</p>
              <p className="text-3xl font-bold text-red-900 mt-1">{summary?.failed || 0}</p>
              <p className="text-sm text-red-700 mt-1">Click Retry to reprocess</p>
            </div>
          </div>
        </div>
      </div>

      {/* Payouts Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Recent Payouts</h2>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {recentPayouts.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-lg font-medium">No payout records yet</p>
            <p className="text-sm mt-1">
              Payouts are created automatically when claims are approved
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
                    Payout ID
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
                    Amount
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
                    When
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {recentPayouts.map((payout) => (
                  <tr
                    key={payout.payout_id}
                    className="hover:bg-slate-50 transition"
                  >
                    <td className="px-4 py-3 text-sm font-mono text-slate-600">
                      {(payout.razorpay_ref || payout.payout_id || "—").slice(0, 12)}…
                    </td>
                    <td className="px-4 py-3 text-sm font-bold text-slate-900">
                      {formatINR(payout.amount)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {payout.paid_at ? formatTime(payout.paid_at) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${
                          STATUS_BADGE[payout.status] || STATUS_BADGE.queued
                        }`}
                      >
                        {payout.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {payout.status === "failed" ? (
                        <button
                          onClick={() =>
                            handleRetry(payout.razorpay_ref || payout.payout_id)
                          }
                          disabled={
                            retrying ===
                            (payout.razorpay_ref || payout.payout_id)
                          }
                          className="flex items-center gap-1 px-3 py-1 bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium rounded-lg transition disabled:opacity-50"
                        >
                          <RefreshCw size={12} />
                          {retrying === (payout.razorpay_ref || payout.payout_id)
                            ? "Retrying…"
                            : "Retry"}
                        </button>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 p-6 rounded-lg border border-blue-200 mt-6">
        <h3 className="font-semibold text-blue-900 mb-2">
          Razorpay Payout System
        </h3>
        <p className="text-sm text-blue-800">
          Payouts are processed automatically when claims are approved. Workers
          receive instant notifications via WhatsApp with their UPI reference.
          Failed payouts can be retried using the Retry button above.
        </p>
      </div>
    </div>
  );
}
