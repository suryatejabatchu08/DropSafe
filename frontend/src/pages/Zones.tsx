import { useEffect, useState } from "react";
import { getZonesSummary } from "../lib/api";
import { formatINR } from "../lib/utils";

interface Zone {
  id: string;
  dark_store_name: string;
  platform: string;
  risk_multiplier: number;
  active_policies: number;
  claims_this_week: number;
  loss_ratio: number;
}

// Loading skeleton for table row
function SkeletonTableRow() {
  return (
    <tr className="border-b border-slate-200 animate-pulse">
      <td className="px-6 py-3">
        <div className="h-4 bg-slate-300 rounded w-40"></div>
      </td>
      <td className="px-6 py-3">
        <div className="h-4 bg-slate-300 rounded w-16"></div>
      </td>
      <td className="px-6 py-3 text-center">
        <div className="h-6 bg-slate-300 rounded w-20 mx-auto"></div>
      </td>
      <td className="px-6 py-3 text-center">
        <div className="h-4 bg-slate-300 rounded w-12 mx-auto"></div>
      </td>
      <td className="px-6 py-3 text-center">
        <div className="h-4 bg-slate-300 rounded w-12 mx-auto"></div>
      </td>
      <td className="px-6 py-3 text-center">
        <div className="h-4 bg-slate-300 rounded w-12 mx-auto"></div>
      </td>
    </tr>
  );
}

export default function Zones() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchZones();
  }, []);

  const fetchZones = async () => {
    try {
      const data = await getZonesSummary();
      if (data) setZones(data);
    } catch (err) {
      console.error("Failed to fetch zones:", err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (risk: number) => {
    if (risk < 1.0) return "bg-green-50 border-green-200";
    if (risk < 1.3) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
  };

  const getRiskBadgeColor = (risk: number) => {
    if (risk < 1.0) return "bg-green-100 text-green-800";
    if (risk < 1.3) return "bg-yellow-100 text-yellow-800";
    return "bg-red-100 text-red-800";
  };

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-slate-900 mb-8">
        Zone Risk Heatmap
      </h1>

      {/* Zones Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-8">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700">
                Zone
              </th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-700">
                Platform
              </th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-slate-700">
                Risk Multiplier
              </th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-slate-700">
                Active Policies
              </th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-slate-700">
                Claims (Week)
              </th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-slate-700">
                Loss Ratio
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <>
                {[1, 2, 3, 4, 5].map((i) => (
                  <SkeletonTableRow key={i} />
                ))}
              </>
            ) : (
              zones.map((zone) => (
                <tr
                  key={zone.id}
                  className="border-b border-slate-200 hover:bg-slate-50 transition"
                >
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">
                    {zone.dark_store_name}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {zone.platform}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`inline-block px-3 py-1 rounded-lg text-sm font-bold ${getRiskBadgeColor(zone.risk_multiplier)}`}
                    >
                      {zone.risk_multiplier.toFixed(2)}x
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-slate-600">
                    {zone.active_policies}
                  </td>
                  <td className="px-6 py-4 text-center text-sm font-medium text-slate-900">
                    {zone.claims_this_week}
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-slate-600">
                    {(zone.loss_ratio * 100).toFixed(1)}%
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Forecast Cards */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-slate-900 mb-4">
          7-Day Digital Exposure Forecast
        </h2>
        {zones.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <p>{loading ? "Loading zones..." : "No zones available"}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {zones.map((zone) => {
              const disruptionProbability = Math.min(
                100,
                zone.risk_multiplier * 60 + Math.random() * 20,
              );
              const estimatedExposure =
                zone.active_policies * 3200 * (disruptionProbability / 100);

              return (
                <div
                  key={zone.id}
                  className={`p-4 rounded-lg border ${getRiskColor(zone.risk_multiplier)}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {zone.dark_store_name}
                      </h3>
                      <p className="text-xs text-slate-600">{zone.platform}</p>
                    </div>
                    <span
                      className={`text-sm font-bold px-2 py-1 rounded ${getRiskBadgeColor(zone.risk_multiplier)}`}
                    >
                      {zone.risk_multiplier.toFixed(2)}x Risk
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-slate-600">
                        Disruption Probability
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-orange-500"
                            style={{ width: `${disruptionProbability}%` }}
                          />
                        </div>
                        <span className="text-sm font-bold text-slate-900">
                          {disruptionProbability.toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs text-slate-600">
                        Estimated Exposure
                      </p>
                      <p className="text-lg font-bold text-slate-900 mt-1">
                        {formatINR(estimatedExposure)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
