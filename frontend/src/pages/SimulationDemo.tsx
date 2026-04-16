/**
 * SimulationDemo — Live disruption simulation demo page.
 * Streams a step-by-step pipeline via SSE from the backend demo router.
 */

import { useState, useEffect } from "react";
import { useSSE } from "../hooks/useSSE";
import SimulationTimeline from "../components/SimulationTimeline";
import { getZones } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TRIGGER_OPTIONS = [
  { value: "rain", label: "🌧️ Heavy Rainfall (≥50mm)", color: "bg-blue-100 text-blue-800" },
  { value: "heat", label: "🌡️ Extreme Heat (≥43°C)", color: "bg-red-100 text-red-800" },
  { value: "aqi", label: "💨 Severe AQI (≥400)", color: "bg-purple-100 text-purple-800" },
  { value: "curfew", label: "🚨 Zone Curfew", color: "bg-orange-100 text-orange-800" },
  { value: "order_collapse", label: "📉 Order Collapse", color: "bg-slate-100 text-slate-800" },
];

const SCENARIO_COLORS: Record<string, string> = {
  normal: "from-blue-600 to-violet-700",
  fraud: "from-red-700 to-orange-700",
  gps_spoof: "from-red-900 to-rose-700",
};

interface Zone {
  id: string;
  dark_store_name: string;
  platform: string;
}

export default function SimulationDemo() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<string>("");
  const [triggerType, setTriggerType] = useState("rain");
  const [severity, setSeverity] = useState(0.75);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);

  const { events, isStreaming, isComplete, error, reset, start } = useSSE();

  useEffect(() => {
    getZones().then((data) => {
      console.log("Zones API response:", data);

      // Handle different response formats
      let zoneList: Zone[] = [];

      if (Array.isArray(data)) {
        zoneList = data.map((z: any) => ({
          id: z.zone_id || z.id,
          dark_store_name: z.name || z.dark_store_name,
          platform: z.platform || "Blinkit"
        }));
      } else if (data?.zones && Array.isArray(data.zones)) {
        zoneList = data.zones.map((z: any) => ({
          id: z.zone_id || z.id,
          dark_store_name: z.name || z.dark_store_name,
          platform: z.platform || "Blinkit"
        }));
      }

      console.log("Processed zones:", zoneList);
      if (zoneList.length === 0) {
        console.warn("No zones found, using hardcoded fallback");
        // Only use fallback if API truly fails
        zoneList = [
          { id: "550e8400-e29b-41d4-a716-446655440001", dark_store_name: "Zepto Dark Store - HSR Layout", platform: "Zepto" },
          { id: "550e8400-e29b-41d4-a716-446655440004", dark_store_name: "Blinkit Hub - Gachibowli", platform: "Blinkit" }
        ];
      }

      setZones(zoneList);
      if (zoneList?.length) setSelectedZone(zoneList[0].id);
    }).catch((err) => {
      console.error("Failed to fetch zones:", err);
      // Use real zone IDs on error (from database)
      const fallbackZones = [
        { id: "550e8400-e29b-41d4-a716-446655440001", dark_store_name: "Zepto Dark Store - HSR Layout", platform: "Zepto" },
        { id: "550e8400-e29b-41d4-a716-446655440004", dark_store_name: "Blinkit Hub - Gachibowli", platform: "Blinkit" }
      ];
      setZones(fallbackZones);
      setSelectedZone(fallbackZones[0].id);
    });
  }, []);

  const triggerSimulation = (scenario: string) => {
    if (!selectedZone || isStreaming) return;
    setActiveScenario(scenario);
    reset();
    start(`${API_BASE}/demo/simulate`, {
      zone_id: selectedZone,
      trigger_type: triggerType,
      severity,
      scenario,
    });
  };

  const selectedZoneObj = zones && Array.isArray(zones) ? zones.find((z) => z.id === selectedZone) : null;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Hero Header */}
      <div className={`py-8 px-6 bg-gradient-to-r ${
        activeScenario ? SCENARIO_COLORS[activeScenario] : "from-slate-800 to-slate-900"
      } transition-all duration-700`}>
        <h1 className="text-3xl font-black tracking-tight mb-1">
          ⚡ DropSafe Live Simulation
        </h1>
        <p className="text-sm text-white/70">
          Watch the full insurance pipeline execute in real time
        </p>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 grid md:grid-cols-2 gap-6">
        {/* --- CONTROLS PANEL --- */}
        <div className="space-y-5">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
              🎛️ Simulation Controls
            </h2>

            {/* Zone Selector */}
            <div className="mb-4">
              <label className="text-xs text-slate-400 mb-1.5 block">Zone</label>
              <select
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                disabled={isStreaming}
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500 disabled:opacity-50"
              >
                {zones.length === 0 ? (
                  <option value="">Loading zones...</option>
                ) : (
                  zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.dark_store_name} ({z.platform})
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Trigger Type */}
            <div className="mb-4">
              <label className="text-xs text-slate-400 mb-1.5 block">Trigger Event</label>
              <div className="space-y-2">
                {TRIGGER_OPTIONS.map((opt) => (
                  <label key={opt.value} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="trigger"
                      value={opt.value}
                      checked={triggerType === opt.value}
                      onChange={() => setTriggerType(opt.value)}
                      disabled={isStreaming}
                      className="accent-violet-500"
                    />
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${opt.color}`}>
                      {opt.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Severity Slider */}
            <div className="mb-5">
              <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                <label>Severity</label>
                <span className="font-bold text-white">{(severity * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min={0.3}
                max={1.0}
                step={0.05}
                value={severity}
                onChange={(e) => setSeverity(parseFloat(e.target.value))}
                disabled={isStreaming}
                className="w-full accent-violet-500 disabled:opacity-50"
              />
            </div>

            {/* Trigger Buttons */}
            <div className="space-y-3">
              <button
                id="btn-normal"
                onClick={() => triggerSimulation("normal")}
                disabled={!selectedZone || isStreaming}
                className="w-full py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isStreaming && activeScenario === "normal"
                  ? "⏳ Running..."
                  : "⚡ TRIGGER DISRUPTION (Normal Claim)"}
              </button>

              <button
                id="btn-fraud"
                onClick={() => triggerSimulation("fraud")}
                disabled={!selectedZone || isStreaming}
                className="w-full py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-red-700 to-orange-700 hover:from-red-600 hover:to-orange-600 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isStreaming && activeScenario === "fraud"
                  ? "⏳ Running..."
                  : "🚨 SIMULATE FRAUD ATTEMPT"}
              </button>

              <button
                id="btn-gps-spoof"
                onClick={() => triggerSimulation("gps_spoof")}
                disabled={!selectedZone || isStreaming}
                className="w-full py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-rose-800 to-red-800 hover:from-rose-700 hover:to-red-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isStreaming && activeScenario === "gps_spoof"
                  ? "⏳ Running..."
                  : "📍 SIMULATE GPS SPOOFING ATTACK (Fraud Ring)"}
              </button>

              {(events.length > 0 || error) && (
                <button
                  onClick={() => { reset(); setActiveScenario(null); }}
                  className="w-full py-2 rounded-xl text-sm text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400 transition"
                >
                  ↩  Reset
                </button>
              )}
            </div>
          </div>

          {/* Scenario Info */}
          {activeScenario && (
            <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
              <p className="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wider">
                Scenario
              </p>
              {activeScenario === "normal" && (
                <p className="text-sm text-slate-300">
                  🟢 <strong>Normal claim:</strong> A legitimate weather event hits{" "}
                  {selectedZoneObj?.dark_store_name}. Worker's parametric trigger fires,
                  fraud engine approves, Razorpay payout initiated in ~7 seconds.
                </p>
              )}
              {activeScenario === "fraud" && (
                <p className="text-sm text-slate-300">
                  🔴 <strong>Fraud attempt:</strong> Worker files a claim with GPS mismatch,
                  off-peak hour, and high frequency. Layer 1 + Layer 2 both flag it.
                  Auto-rejected, worker receives dispute option.
                </p>
              )}
              {activeScenario === "gps_spoof" && (
                <p className="text-sm text-slate-300">
                  🚨 <strong>GPS spoofing ring:</strong> 500 workers simultaneously file claims,
                  all GPS coordinates outside the zone. Cluster fraud detector fires,
                  all 500 payouts frozen instantly.
                </p>
              )}
            </div>
          )}
        </div>

        {/* --- TIMELINE PANEL --- */}
        <div>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 min-h-[400px]">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
              📡 Live Pipeline
            </h2>

            {error && (
              <div className="p-3 rounded-lg bg-red-900/30 border border-red-700 mb-4">
                <p className="text-sm text-red-300">⚠️ {error}</p>
              </div>
            )}

            {events.length === 0 && !isStreaming && !error && (
              <div className="flex flex-col items-center justify-center h-72 text-center">
                <div className="text-5xl mb-4">🚀</div>
                <p className="text-slate-400 text-sm">
                  Select a zone and click a trigger button to watch the pipeline run
                </p>
              </div>
            )}

            <SimulationTimeline events={events} isStreaming={isStreaming} />

            {isComplete && !isStreaming && (
              <p className="text-xs text-slate-500 mt-4 text-center">
                Simulation complete • {events.filter(e => typeof e.step === "number").length} steps executed
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="max-w-5xl mx-auto px-4 pb-8">
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
          <p className="text-xs text-slate-400 mb-3 font-semibold uppercase tracking-wider">
            Architecture — What's running behind each step
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-300">
            <div className="flex items-start gap-2">
              <span>1–2.</span>
              <span>WeatherAPI / IQAir trigger verification</span>
            </div>
            <div className="flex items-start gap-2">
              <span>3.</span>
              <span>Supabase policies + workers lookup</span>
            </div>
            <div className="flex items-start gap-2">
              <span>4.</span>
              <span>FraudEngine Layer 1 (7 rules) + Layer 2 (Isolation Forest)</span>
            </div>
            <div className="flex items-start gap-2">
              <span>5–7.</span>
              <span>Razorpay UPI payout + Twilio WhatsApp + Dashboard update</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
