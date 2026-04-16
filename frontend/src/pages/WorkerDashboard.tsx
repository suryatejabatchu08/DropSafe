/**
 * WorkerDashboard — Mobile-first worker-facing income shield dashboard.
 * Accessed via /worker/:workerId — no login required for demo.
 */

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getWorkerDashboard } from "../lib/api";

interface WorkerData {
  worker: {
    id: string;
    name: string;
    zone_name: string;
    platform: string;
  };
  active_policy: {
    week_start: string;
    week_end: string;
    premium_paid: number;
    coverage_cap: number;
    days_remaining: number;
  } | null;
  earnings_protected_week: number;
  disruption_count_week: number;
  coverage_cap: number;
  recent_payouts: Array<{
    trigger_type: string;
    trigger_emoji: string;
    date: string;
    amount: number;
    status: string;
  }>;
  active_zone_alerts: Array<{
    trigger_type: string;
    trigger_emoji: string;
    severity: number;
    time_since: string;
  }>;
}

const PLATFORM_BADGE: Record<string, { label: string; bg: string }> = {
  zepto: { label: "Zepto 🟢", bg: "bg-green-100 text-green-800" },
  blinkit: { label: "Blinkit 🟠", bg: "bg-orange-100 text-orange-800" },
};

const STATUS_BADGE: Record<string, string> = {
  success: "bg-green-100 text-green-800",
  paid: "bg-green-100 text-green-800",
  review: "bg-yellow-100 text-yellow-800",
  pending: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-slate-100 p-5 ${className}`}>
      {children}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5 animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-24 mb-3" />
      <div className="h-8 bg-slate-200 rounded w-40 mb-2" />
      <div className="h-3 bg-slate-100 rounded w-32" />
    </div>
  );
}

function formatDate(isoDate: string) {
  try {
    return new Date(isoDate).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return isoDate;
  }
}

export default function WorkerDashboard() {
  const { workerId } = useParams<{ workerId: string }>();
  const [data, setData] = useState<WorkerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!workerId) return;
    fetchDashboard();
  }, [workerId]);

  const fetchDashboard = async () => {
    try {
      const res = await getWorkerDashboard(workerId!);
      if (res) {
        setData(res);
      } else {
        setNotFound(true);
      }
    } catch (err: any) {
      if (err?.response?.status === 404) setNotFound(true);
    } finally {
      setLoading(false);
    }
  };

  const TWILIO_NUMBER = import.meta.env.VITE_TWILIO_NUMBER || "+14155238886";

  if (notFound) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center max-w-xs">
          <div className="text-6xl mb-4">😕</div>
          <h1 className="text-xl font-bold text-slate-900 mb-2">Dashboard not found</h1>
          <p className="text-slate-500 text-sm">
            The worker ID in this link is invalid or has been removed.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-slate-900 text-white px-4 pt-8 pb-6">
        <div className="max-w-[480px] mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-yellow-400 flex items-center justify-center">
              <span className="text-slate-900 font-black text-lg">D</span>
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight">DropSafe</h1>
              <p className="text-slate-400 text-xs">Your Income Shield</p>
            </div>
          </div>

          {loading ? (
            <div className="animate-pulse">
              <div className="h-7 bg-slate-700 rounded w-40 mb-2" />
              <div className="h-4 bg-slate-700 rounded w-32" />
            </div>
          ) : data ? (
            <>
              <h2 className="text-2xl font-bold">{data.worker.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-slate-400 text-sm">{data.worker.zone_name}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                    PLATFORM_BADGE[data.worker.platform]?.bg ?? "bg-slate-700 text-slate-200"
                  }`}
                >
                  {PLATFORM_BADGE[data.worker.platform]?.label ?? data.worker.platform}
                </span>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Cards */}
      <div className="max-w-[480px] mx-auto px-4 py-4 space-y-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : data ? (
          <>
            {/* CARD 1 — Coverage Status */}
            <Card>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Coverage Status
              </p>
              {data.active_policy ? (
                <>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="bg-green-100 text-green-800 text-sm font-bold px-3 py-1 rounded-full">
                      ✅ ACTIVE
                    </span>
                    <span className="text-xs text-slate-500">
                      {data.active_policy.days_remaining} days remaining
                    </span>
                  </div>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Week</span>
                      <span className="font-medium text-slate-800">
                        {formatDate(data.active_policy.week_start)} –{" "}
                        {formatDate(data.active_policy.week_end)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Premium paid</span>
                      <span className="font-semibold text-slate-900">
                        ₹{data.active_policy.premium_paid.toFixed(0)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Coverage cap</span>
                      <span className="font-semibold text-slate-900">
                        ₹{data.active_policy.coverage_cap.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="bg-slate-100 text-slate-600 text-sm font-bold px-3 py-1 rounded-full">
                    ⚪ NOT COVERED
                  </span>
                  <span className="text-xs text-slate-500">No active policy this week</span>
                </div>
              )}
            </Card>

            {/* CARD 2 — Earnings Protected */}
            <Card>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Earnings Protected This Week
              </p>
              <p className="text-4xl font-black text-slate-900">
                ₹{data.earnings_protected_week.toLocaleString("en-IN")}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                From {data.disruption_count_week} disruption{" "}
                {data.disruption_count_week === 1 ? "event" : "events"}
              </p>
              {data.coverage_cap > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>₹{data.earnings_protected_week.toFixed(0)} paid</span>
                    <span>₹{data.coverage_cap.toLocaleString("en-IN")} cap</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className="h-2 bg-yellow-400 rounded-full transition-all"
                      style={{
                        width: `${Math.min(
                          (data.earnings_protected_week / data.coverage_cap) * 100,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </Card>

            {/* CARD 3 — Payout History */}
            <Card>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Recent Payouts
              </p>
              {data.recent_payouts.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-4">
                  No payouts yet
                </p>
              ) : (
                <div className="space-y-3">
                  {data.recent_payouts.map((payout, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{payout.trigger_emoji}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-800 capitalize">
                            {payout.trigger_type.replace("_", " ")}
                          </p>
                          <p className="text-xs text-slate-500">{payout.date}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-slate-900">₹{Math.round(payout.amount)}</p>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            STATUS_BADGE[payout.status] ?? "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {payout.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* CARD 4 — Active Zone Alerts */}
            <Card>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Active Zone Alerts
              </p>
              {data.active_zone_alerts.length === 0 ? (
                <p className="text-sm text-slate-700">
                  🟢 No active alerts in your zone
                </p>
              ) : (
                <div className="space-y-2">
                  {data.active_zone_alerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-2 rounded-lg bg-red-50 border border-red-100"
                    >
                      <span className="text-xl">{alert.trigger_emoji}</span>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-red-900 capitalize">
                          {alert.trigger_type.replace("_", " ")}
                        </p>
                        <p className="text-xs text-red-600">
                          Severity {(alert.severity * 100).toFixed(0)}% • {alert.time_since}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* CARD 5 — Premium & CTA */}
            <Card>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                This Week's Premium
              </p>
              {data.active_policy ? (
                <p className="text-sm text-slate-700">
                  ✅ ₹{data.active_policy.premium_paid.toFixed(0)} paid on{" "}
                  {formatDate(data.active_policy.week_start)}
                </p>
              ) : (
                <>
                  <p className="text-sm text-slate-500 mb-4">
                    You're not covered this week. Activate via WhatsApp to get protected.
                  </p>
                  <a
                    href={`https://wa.me/${TWILIO_NUMBER.replace(/\D/g, "")}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-4 rounded-xl text-center transition"
                  >
                    💬 Open WhatsApp to Activate
                  </a>
                </>
              )}
            </Card>

            {/* Footer */}
            <div className="text-center text-xs text-slate-400 pb-8">
              <p>DropSafe • Income Protection for Delivery Partners</p>
              <p className="mt-1">Worker ID: {workerId?.substring(0, 8)}...</p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
