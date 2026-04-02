import { useEffect, useState } from "react";
import { AlertCircle, Loader } from "lucide-react";
import {
  getTriggerEmoji,
  getTriggerColor,
  formatTime,
  getSeverityColor,
} from "@/lib/utils";
import api from "@/lib/api";

interface Trigger {
  id: string;
  zone_id: string;
  zone_name: string;
  trigger_type: string;
  severity: number;
  start_time: string;
  verified: boolean;
}

export default function TriggerFeed() {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTriggers();
    const interval = setInterval(fetchTriggers, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchTriggers = async () => {
    try {
      const response = await api.get("/triggers/active");
      setTriggers(response.data.data || []);
    } catch (err) {
      console.error("Failed to fetch triggers:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg border border-slate-200">
        <h2 className="text-lg font-semibold mb-4">🔴 Live Trigger Feed</h2>
        <div className="flex justify-center py-8">
          <Loader className="animate-spin text-slate-400" size={32} />
        </div>
      </div>
    );
  }

  if (triggers.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg border border-slate-200">
        <h2 className="text-lg font-semibold mb-4">🔴 Live Trigger Feed</h2>
        <div className="text-center py-8 text-slate-500">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>No active triggers right now 🟢</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg border border-slate-200">
      <h2 className="text-lg font-semibold mb-4">🔴 Live Trigger Feed</h2>
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {triggers.map((trigger) => (
          <div
            key={trigger.id}
            className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-slate-100 transition"
          >
            {/* Zone & Type */}
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

            {/* Severity Bar */}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
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

            {/* Time & Status */}
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
    </div>
  );
}
