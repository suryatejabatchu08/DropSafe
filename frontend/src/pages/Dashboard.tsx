import { useEffect, useState } from "react";
import { getDashboardStats, getActiveTriggers } from "../lib/api";
import { formatTime, getTriggerEmoji } from "../lib/utils";

interface Stats {
  active_policies: number;
  total_payout_week: number;
  active_triggers: number;
  fraud_alerts: number;
}

interface Trigger {
  id: string;
  zone_id: string;
  zone_name: string;
  trigger_type: string;
  severity: number;
  start_time: string;
  verified: boolean;
}

// Loading skeleton for stat cards
function SkeletonCard() {
  return (
    <div className="bg-slate-100 p-6 rounded-lg border border-slate-200 animate-pulse">
      <div className="h-4 bg-slate-300 rounded w-24 mb-4"></div>
      <div className="h-8 bg-slate-300 rounded w-32"></div>
    </div>
  );
}

// Loading skeleton for trigger feed items
function SkeletonTrigger() {
  return (
    <div className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg border border-slate-200 animate-pulse">
      <div className="flex-1">
        <div className="h-4 bg-slate-300 rounded w-48 mb-2"></div>
        <div className="h-3 bg-slate-300 rounded w-32"></div>
      </div>
      <div className="flex-1">
        <div className="h-2 bg-slate-300 rounded-full mb-2"></div>
        <div className="h-3 bg-slate-300 rounded w-16"></div>
      </div>
      <div className="text-right">
        <div className="h-3 bg-slate-300 rounded w-24 mb-2"></div>
        <div className="h-6 bg-slate-300 rounded w-20"></div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, triggersRes] = await Promise.all([
        getDashboardStats(),
        getActiveTriggers(),
      ]);

      if (statsRes) setStats(statsRes);
      if (triggersRes?.data) setTriggers(triggersRes.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-bold text-slate-900">Dashboard</h1>
        {lastUpdated && (
          <p className="text-sm text-slate-500">
            Updated: {lastUpdated.toLocaleTimeString("en-IN")}
          </p>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-600">
                Active Policies
              </p>
              <p className="text-3xl font-bold text-blue-900 mt-2">
                {stats?.active_policies || 0}
              </p>
            </div>
            <div className="bg-green-50 p-6 rounded-lg border border-green-200">
              <p className="text-sm font-medium text-green-600">
                Total Payout (Week)
              </p>
              <p className="text-3xl font-bold text-green-900 mt-2">
                ₹{(stats?.total_payout_week || 0).toFixed(0)}
              </p>
            </div>
            <div className="bg-red-50 p-6 rounded-lg border border-red-200">
              <p className="text-sm font-medium text-red-600">
                Active Triggers
              </p>
              <p className="text-3xl font-bold text-red-900 mt-2">
                {stats?.active_triggers || 0}
              </p>
            </div>
            <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
              <p className="text-sm font-medium text-yellow-600">
                Fraud Alerts
              </p>
              <p className="text-3xl font-bold text-yellow-900 mt-2">
                {stats?.fraud_alerts || 0}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Live Trigger Feed */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 mb-8">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          🔴 Live Trigger Feed
        </h2>
        {loading ? (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {[1, 2, 3].map((i) => (
              <SkeletonTrigger key={i} />
            ))}
          </div>
        ) : triggers.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <p>No active triggers right now 🟢</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {triggers.map((trigger) => (
              <div
                key={trigger.id}
                className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-slate-100 transition"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">
                      {getTriggerEmoji(trigger.trigger_type)}
                    </span>
                    <div>
                      <p className="font-semibold text-slate-900">
                        {trigger.zone_name}
                      </p>
                      <p className="text-sm text-slate-500">
                        {trigger.trigger_type.replace("_", " ").toUpperCase()}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          trigger.severity < 0.3
                            ? "bg-green-500"
                            : trigger.severity < 0.6
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        }`}
                        style={{ width: `${trigger.severity * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-slate-600 w-12">
                      {(trigger.severity * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="text-right min-w-32">
                  <p className="text-sm text-slate-500">
                    {formatTime(trigger.start_time)}
                  </p>
                  <span
                    className={`inline-block px-2 py-1 rounded text-xs font-semibold mt-1 ${
                      trigger.verified
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {trigger.verified ? "✓ Verified" : "Pending"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Refresh indicator */}
      <div className="text-center text-slate-500 text-sm">
        {loading && <p>🔄 Refreshing data...</p>}
      </div>
    </div>
  );
}
