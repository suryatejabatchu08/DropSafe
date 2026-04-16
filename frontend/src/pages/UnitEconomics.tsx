import { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { getUnitEconomics } from '../lib/api';

interface UnitEconomicsData {
  per_worker: {
    avg_premium: number;
    avg_payout_per_claim: number;
    avg_claims_per_worker_week: number;
    expected_payout_per_worker: number;
    gross_margin_per_worker: number;
    margin_pct: number;
  };
  portfolio: {
    total_premiums_week: number;
    total_payouts_week: number;
    operating_expenses_week: number;
    loss_ratio_pct: number;
    net_margin: number;
    net_margin_pct: number;
    risk_level: string;
  };
  by_zone: Array<{
    zone_id: string;
    zone_name: string;
    avg_premium: number;
    avg_payout_per_claim: number;
    loss_ratio_pct: number;
    verdict: string;
  }>;
  breakeven: {
    fixed_costs_per_zone_week: number;
    profit_per_worker: number;
    breakeven_workers_per_zone: number;
    interpretation: string;
  };
}

export default function UnitEconomics() {
  const [data, setData] = useState<UnitEconomicsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getUnitEconomics();
        if (!data) throw new Error('Failed to fetch unit economics');
        setData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="text-center py-12">Loading unit economics...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'HEALTHY':
        return 'bg-green-50 border-green-200';
      case 'MONITOR':
        return 'bg-yellow-50 border-yellow-200';
      case 'UNSUSTAINABLE':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-slate-50 border-slate-200';
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'HEALTHY':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'MONITOR':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case 'UNSUSTAINABLE':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return null;
    }
  };

  return (
    <div className="p-6 bg-slate-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-yellow-500" />
            Unit Economics
          </h1>
          <p className="text-slate-600 mt-2">Business viability & profitability analysis</p>
        </div>

        {/* SECTION 1: Per-Worker Economics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-sm text-slate-600">Avg Premium/Worker</div>
            <div className="text-2xl font-bold text-slate-900">₹{data.per_worker.avg_premium}</div>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-sm text-slate-600">Avg Payout/Claim</div>
            <div className="text-2xl font-bold text-slate-900">₹{data.per_worker.avg_payout_per_claim}</div>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-sm text-slate-600">Avg Claims/Worker</div>
            <div className="text-2xl font-bold text-slate-900">{data.per_worker.avg_claims_per_worker_week}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-sm text-slate-600">Expected Payout/Worker</div>
            <div className="text-2xl font-bold text-slate-900">
              ₹{data.per_worker.expected_payout_per_worker}
            </div>
          </div>
          <div className={`rounded-lg border p-4 ${data.per_worker.gross_margin_per_worker >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
            <div className="text-sm font-semibold">
              {data.per_worker.gross_margin_per_worker >= 0 ? 'Gross Margin ✅' : 'Gross Loss 🔴'}
            </div>
            <div className={`text-2xl font-bold ${data.per_worker.gross_margin_per_worker >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ₹{data.per_worker.gross_margin_per_worker} ({data.per_worker.margin_pct}%)
            </div>
          </div>
        </div>

        {/* SECTION 2: Portfolio Economics */}
        <div className={`rounded-lg border ${getRiskColor(data.portfolio.risk_level)} p-6 mb-6`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-900">Portfolio Economics (This Week)</h2>
            <div className="flex items-center gap-2">
              {getRiskIcon(data.portfolio.risk_level)}
              <span className="font-semibold text-slate-900">{data.portfolio.risk_level}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-slate-600">Total Premiums</div>
              <div className="text-xl font-bold">₹{data.portfolio.total_premiums_week}</div>
            </div>
            <div>
              <div className="text-sm text-slate-600">Total Payouts</div>
              <div className="text-xl font-bold">₹{data.portfolio.total_payouts_week}</div>
            </div>
            <div>
              <div className="text-sm text-slate-600">Operating Costs (15%)</div>
              <div className="text-xl font-bold">₹{data.portfolio.operating_expenses_week}</div>
            </div>
            <div>
              <div className="text-sm text-slate-600 font-semibold">Net Margin</div>
              <div className={`text-xl font-bold ${data.portfolio.net_margin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ₹{data.portfolio.net_margin} ({data.portfolio.net_margin_pct}%)
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-current/20">
            <div className="text-sm font-semibold mb-2">Loss Ratio: {data.portfolio.loss_ratio_pct}%</div>
            <div className="text-xs text-slate-600">
              {data.portfolio.loss_ratio_pct < 65 && '🟡 UNDERPRICED: Workers underserved, consider increasing coverage'}
              {data.portfolio.loss_ratio_pct >= 65 && data.portfolio.loss_ratio_pct < 75 && '🟢 HEALTHY: Optimal pricing for market conditions'}
              {data.portfolio.loss_ratio_pct >= 75 && data.portfolio.loss_ratio_pct < 85 && '🟠 MONITOR: Watch claim trends closely'}
              {data.portfolio.loss_ratio_pct >= 85 && '🔴 UNSUSTAINABLE: Pricing must be adjusted'}
            </div>
          </div>
        </div>

        {/* SECTION 3: Zone Profitability */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
          <h2 className="text-xl font-bold text-slate-900 mb-4">Profitability by Zone</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-2 font-semibold text-slate-700">Zone</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-700">Avg Premium</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-700">Avg Payout</th>
                  <th className="text-right py-2 px-2 font-semibold text-slate-700">Loss Ratio</th>
                  <th className="text-left py-2 px-2 font-semibold text-slate-700">Verdict</th>
                </tr>
              </thead>
              <tbody>
                {data.by_zone.map((zone) => (
                  <tr key={zone.zone_id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 px-2 text-slate-900 font-medium">{zone.zone_name}</td>
                    <td className="text-right py-2 px-2">₹{zone.avg_premium}</td>
                    <td className="text-right py-2 px-2">₹{zone.avg_payout_per_claim}</td>
                    <td className="text-right py-2 px-2 font-semibold">{zone.loss_ratio_pct}%</td>
                    <td className="py-2 px-2">
                      <span className={`text-xs font-semibold ${
                        zone.verdict.includes('Profitable') ? 'text-green-600' :
                        zone.verdict.includes('Borderline') ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {zone.verdict}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION 4: Break-even Analysis */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-slate-900 mb-3">Break-even Analysis</h2>
          <div className="space-y-2">
            <p className="text-sm text-slate-700">
              <span className="font-semibold">Fixed Costs/Zone/Week:</span> ₹{data.breakeven.fixed_costs_per_zone_week}
            </p>
            <p className="text-sm text-slate-700">
              <span className="font-semibold">Profit/Worker/Week:</span> ₹{data.breakeven.profit_per_worker}
            </p>
            <p className={`text-lg font-bold ${data.breakeven.breakeven_workers_per_zone > 0 ? 'text-blue-600' : 'text-red-600'}`}>
              Break-even Workers: {data.breakeven.breakeven_workers_per_zone > 0 ? data.breakeven.breakeven_workers_per_zone : 'Not viable'}
            </p>
            <p className="text-sm text-slate-600 mt-3 italic">
              {data.breakeven.interpretation}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
