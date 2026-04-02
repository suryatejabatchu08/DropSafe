import { useEffect, useState } from "react";
import { getPayoutSummary, retryPayout } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import { AlertTriangle, Loader } from "lucide-react";

// Loading skeleton
function SkeletonStatCard() {
  return (
    <div className="bg-slate-100 p-6 rounded-lg border border-slate-200 animate-pulse">
      <div className="h-4 bg-slate-300 rounded w-20 mb-4"></div>
      <div className="h-10 bg-slate-300 rounded w-32"></div>
    </div>
  );
}

interface PayoutSummary {
  today: { total: number; successful: number; count: number };
  week: { total: number; successful: number; count: number };
  pending: number;
  failed: number;
  success_rate: number;
}

export default function Payouts() {
  const [summary, setSummary] = useState<PayoutSummary | null>(null);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-4xl font-bold text-slate-900 mb-8">Payouts</h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SkeletonStatCard />
          <SkeletonStatCard />
          <SkeletonStatCard />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SkeletonStatCard />
          <SkeletonStatCard />
          <SkeletonStatCard />
        </div>
      </div>
    );
  }

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
        {/* Pending */}
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <div className="flex items-start gap-3">
            <AlertTriangle
              className="text-yellow-600 flex-shrink-0 mt-1"
              size={24}
            />
            <div>
              <p className="text-sm font-semibold text-yellow-900">
                Pending Payouts
              </p>
              <p className="text-3xl font-bold text-yellow-900 mt-1">
                {summary?.pending || 0}
              </p>
              <p className="text-sm text-yellow-700 mt-1">
                Will be processed soon
              </p>
            </div>
          </div>
        </div>

        {/* Failed */}
        <div className="bg-red-50 p-6 rounded-lg border border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle
              className="text-red-600 flex-shrink-0 mt-1"
              size={24}
            />
            <div>
              <p className="text-sm font-semibold text-red-900">
                Failed Payouts
              </p>
              <p className="text-3xl font-bold text-red-900 mt-1">
                {summary?.failed || 0}
              </p>
              <p className="text-sm text-red-700 mt-1">Requires manual retry</p>
            </div>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-2">
          Rayorpay Payout System
        </h3>
        <p className="text-sm text-blue-800">
          Payouts are processed automatically when claims are approved. Workers
          receive instant notifications via WhatsApp with their UPI reference.
        </p>
      </div>
    </div>
  );
}
