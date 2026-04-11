import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { getDashboardStats, getDailyClaimsSummary, getDailyPayoutsSummary } from "../lib/api";
import StatCard from "../components/StatCard";
import TriggerFeed from "../components/TriggerFeed";

interface Stats {
  active_policies: number;
  total_payout_week: number;
  active_triggers: number;
  fraud_alerts: number;
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

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [claimsData, setClaimsData] = useState<any[]>([]);
  const [payoutsData, setPayoutsData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, claimsRes, payoutsRes] = await Promise.all([
        getDashboardStats(),
        getDailyClaimsSummary(),
        getDailyPayoutsSummary(),
      ]);

      if (statsRes) setStats(statsRes);
      if (claimsRes) setClaimsData(claimsRes);
      if (payoutsRes) setPayoutsData(payoutsRes);
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

      {/* Stats Row — using StatCard component */}
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
            <StatCard
              title="Active Policies"
              value={stats?.active_policies ?? 0}
              icon="📋"
              color="blue"
            />
            <StatCard
              title="Total Payout (Week)"
              value={`₹${(stats?.total_payout_week ?? 0).toFixed(0)}`}
              icon="💸"
              color="green"
            />
            <StatCard
              title="Active Triggers"
              value={stats?.active_triggers ?? 0}
              icon="🚨"
              color="red"
            />
            <StatCard
              title="Fraud Alerts"
              value={stats?.fraud_alerts ?? 0}
              icon="⚠️"
              color="yellow"
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Claims Bar Chart — last 7 days by status */}
        <div className="bg-white p-6 rounded-lg border border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            📊 Claims — Last 7 Days
          </h2>
          {claimsData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-slate-400">
              No claims data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={claimsData}
                margin={{ top: 0, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)} // MM-DD
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="auto_approved" name="Auto Approved" fill="#22c55e" stackId="a" />
                <Bar dataKey="approved" name="Approved" fill="#16a34a" stackId="a" />
                <Bar dataKey="review" name="Review" fill="#f59e0b" stackId="a" />
                <Bar dataKey="rejected" name="Rejected" fill="#ef4444" stackId="a" />
                <Bar dataKey="paid" name="Paid" fill="#3b82f6" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Payouts Line Chart — last 7 days by amount */}
        <div className="bg-white p-6 rounded-lg border border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            💰 Payouts — Last 7 Days
          </h2>
          {payoutsData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-slate-400">
              No payout data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart
                data={payoutsData}
                margin={{ top: 0, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => `₹${v}`}
                />
                <Tooltip formatter={(v: any) => [`₹${v}`, "Payout"]} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="total_amount"
                  name="Payout Amount"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  name="# Payouts"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Live Trigger Feed — using TriggerFeed component */}
      <TriggerFeed />

      {/* Refresh indicator */}
      <div className="text-center text-slate-500 text-sm mt-4">
        {loading && <p>🔄 Refreshing data...</p>}
      </div>
    </div>
  );
}
