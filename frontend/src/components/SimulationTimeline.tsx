/**
 * SimulationTimeline — Animated step-by-step demonstration timeline.
 * Used by SimulationDemo to display each pipeline step as it streams in.
 */

// Temporarily use any to bypass module resolution issue
type SSEEvent = any;

const STATUS_ICONS: Record<string, string> = {
  success: "✅",
  failure: "❌",
  processing: "⏳",
  warning: "⚠️",
  info: "ℹ️",
  complete: "✅",
  review: "🔍",
  fraud: "🚨",
  blocked: "⛔",
  fraud_blocked: "🛡️",
  cluster_blocked: "🚨",
  error: "💥",
};

const STATUS_COLORS: Record<string, string> = {
  success: "border-green-500 bg-green-500/10",
  failure: "border-red-500 bg-red-500/10",
  processing: "border-yellow-500 bg-yellow-500/10",
  warning: "border-yellow-400 bg-yellow-400/10",
  info: "border-blue-400 bg-blue-400/10",
  complete: "border-green-400 bg-green-400/10",
  review: "border-yellow-500 bg-yellow-500/10",
  fraud: "border-red-500 bg-red-500/15",
  blocked: "border-red-600 bg-red-600/10",
  fraud_blocked: "border-emerald-500 bg-emerald-500/10",
  cluster_blocked: "border-red-600 bg-red-600/15",
  error: "border-red-700 bg-red-700/10",
};

const TEXT_COLORS: Record<string, string> = {
  success: "text-green-300",
  failure: "text-red-400",
  processing: "text-yellow-300",
  warning: "text-yellow-300",
  info: "text-blue-300",
  complete: "text-green-300",
  review: "text-yellow-300",
  fraud: "text-red-400",
  blocked: "text-red-400",
  fraud_blocked: "text-emerald-300",
  cluster_blocked: "text-red-400",
  error: "text-red-400",
};

interface SimulationTimelineProps {
  events: SSEEvent[];
  isStreaming: boolean;
}

export default function SimulationTimeline({
  events,
  isStreaming,
}: SimulationTimelineProps) {
  const stepEvents = events.filter((e) => typeof e.step === "number");
  const finalEvent = events.find((e) => e.step === "complete");

  return (
    <div className="space-y-3">
      {/* Step Events */}
      {stepEvents.map((event, idx) => {
        const icon = STATUS_ICONS[event.status] || "•";
        const borderColor = STATUS_COLORS[event.status] || "border-slate-600";
        const textColor = TEXT_COLORS[event.status] || "text-slate-300";

        return (
          <div
            key={idx}
            className={`flex items-start gap-3 p-3 rounded-lg border ${borderColor} animate-fade-in`}
            style={{ animationDelay: `${idx * 50}ms` }}
          >
            {/* Step number */}
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              {typeof event.step === "number" ? event.step : "✓"}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className={`text-sm font-semibold ${textColor}`}>
                  {icon} {event.message}
                </p>
                {event.timestamp && (
                  <span className="text-xs text-slate-500 whitespace-nowrap">
                    {event.timestamp}
                  </span>
                )}
              </div>
              {event.detail && (
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  {event.detail}
                </p>
              )}
            </div>
          </div>
        );
      })}

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-600 bg-slate-700/30">
          <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-yellow-400 animate-pulse" />
          </div>
          <p className="text-sm text-slate-400 animate-pulse">Processing...</p>
        </div>
      )}

      {/* Final Banner */}
      {finalEvent && (
        <div
          className={`mt-4 p-4 rounded-xl border-2 text-center ${
            finalEvent.status === "fraud_blocked" || finalEvent.status === "cluster_blocked"
              ? "border-emerald-400 bg-emerald-400/10"
              : finalEvent.status === "fraud" || finalEvent.status === "blocked"
              ? "border-red-400 bg-red-400/10"
              : finalEvent.status === "review"
              ? "border-yellow-400 bg-yellow-400/10"
              : "border-green-400 bg-green-400/10"
          }`}
        >
          <p className="text-lg font-bold text-white">{finalEvent.message}</p>
          {finalEvent.payout_amount && (
            <p className="text-2xl font-black text-green-400 mt-2">
              ₹{finalEvent.payout_amount.toLocaleString("en-IN")} protected
            </p>
          )}
          {finalEvent.funds_protected && (
            <p className="text-2xl font-black text-emerald-400 mt-2">
              ₹{finalEvent.funds_protected.toLocaleString("en-IN")} protected
            </p>
          )}
          {finalEvent.fraud_score !== undefined && (
            <p className="text-sm text-slate-400 mt-1">
              Combined fraud score: {finalEvent.fraud_score.toFixed(3)}
            </p>
          )}
          {finalEvent.timestamp && (
            <p className="text-xs text-slate-500 mt-1">{finalEvent.timestamp}</p>
          )}
        </div>
      )}
    </div>
  );
}
