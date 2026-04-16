/**
 * PredictivePanel — Next-week disruption forecast table.
 * Shown below charts on the Overview dashboard.
 */

interface ZoneForecast {
  zone_id: string;
  zone_name: string;
  platform: string;
  disruption_probability: number;
  disruption_probability_pct: number;
  risk_level: "low" | "medium" | "high";
  active_policies: number;
  estimated_claims: number;
  estimated_exposure_inr: number;
  weather_risk_factor: number;
}

interface PredictivePanelProps {
  zones: ZoneForecast[];
  loading?: boolean;
}

const RISK_BADGE: Record<string, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
};

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-200 rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

export default function PredictivePanel({ zones, loading }: PredictivePanelProps) {
  return (
    <div className="bg-white p-6 rounded-lg border border-slate-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          🔮 Next Week's Disruption Forecast
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded">
          Powered by WeatherAPI + Zone Risk Model
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left px-4 py-3 text-slate-500 font-medium">Zone</th>
              <th className="text-left px-4 py-3 text-slate-500 font-medium">Risk</th>
              <th className="text-right px-4 py-3 text-slate-500 font-medium">Disruption P</th>
              <th className="text-right px-4 py-3 text-slate-500 font-medium">Est. Claims</th>
              <th className="text-right px-4 py-3 text-slate-500 font-medium">Est. Exposure</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <>
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </>
            ) : zones.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  No zone data available
                </td>
              </tr>
            ) : (
              zones.map((zone) => (
                <tr key={zone.zone_id} className="hover:bg-slate-50 transition">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{zone.zone_name}</p>
                    <p className="text-xs text-slate-500 capitalize">{zone.platform}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold capitalize ${
                        RISK_BADGE[zone.risk_level]
                      }`}
                    >
                      {zone.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-24 bg-slate-100 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            zone.risk_level === "high"
                              ? "bg-red-500"
                              : zone.risk_level === "medium"
                              ? "bg-yellow-400"
                              : "bg-green-500"
                          }`}
                          style={{ width: `${Math.min(zone.disruption_probability_pct, 100)}%` }}
                        />
                      </div>
                      <span className="font-semibold text-slate-900 w-10 text-right">
                        {zone.disruption_probability_pct.toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-700 font-medium">
                    {zone.estimated_claims}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-900 font-semibold">
                    ₹{zone.estimated_exposure_inr.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!loading && zones.some((z) => z.risk_level === "high") && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <span className="text-red-600">⚠️</span>
          <p className="text-sm text-red-800 font-medium">
            {zones.filter((z) => z.risk_level === "high").length} high-risk{" "}
            {zones.filter((z) => z.risk_level === "high").length === 1 ? "zone" : "zones"} detected
            — consider increasing reserves.
          </p>
        </div>
      )}
    </div>
  );
}
