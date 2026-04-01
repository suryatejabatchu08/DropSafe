import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format currency in INR
export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

// Format time (e.g., "2 hours ago", "just now")
export function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString("en-IN");
  } catch {
    return "unknown";
  }
}

// Anonymize worker name/ID
export function anonymizeWorker(name?: string, id?: string): string {
  if (name) {
    return name.substring(0, 3).toUpperCase() + "***";
  }
  if (id) {
    return id.substring(0, 3).toUpperCase() + "***";
  }
  return "W***";
}

// Get severity color
export function getSeverityColor(severity: number): string {
  if (severity < 0.3) return "bg-green-100 text-green-800";
  if (severity < 0.6) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

// Get trigger type emoji
export function getTriggerEmoji(triggerType: string): string {
  const emojis: Record<string, string> = {
    rain: "🌧️",
    heat: "🔥",
    aqi: "😷",
    curfew: "🚨",
    order_collapse: "📉",
    store_closure: "🔒",
  };
  return emojis[triggerType] || "⚠️";
}

// Get trigger type color
export function getTriggerColor(triggerType: string): string {
  const colors: Record<string, string> = {
    rain: "text-blue-600 bg-blue-50",
    heat: "text-red-600 bg-red-50",
    aqi: "text-purple-600 bg-purple-50",
    curfew: "text-orange-600 bg-orange-50",
    order_collapse: "text-yellow-600 bg-yellow-50",
    store_closure: "text-gray-600 bg-gray-50",
  };
  return colors[triggerType] || "text-gray-600 bg-gray-50";
}

// Get claim status color
export function getClaimStatusColor(status: string): string {
  const colors: Record<string, string> = {
    auto_approved: "bg-green-100 text-green-800",
    approved: "bg-green-100 text-green-800",
    review: "bg-yellow-100 text-yellow-800",
    rejected: "bg-red-100 text-red-800",
    paid: "bg-blue-100 text-blue-800",
  };
  return colors[status] || "bg-gray-100 text-gray-800";
}

// Get fraud score color
export function getFraudScoreColor(score: number): string {
  if (score < 0.3) return "bg-green-100 text-green-800";
  if (score < 0.6) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

// Format date
export function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString("en-IN", {
      year: "2-digit",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return "N/A";
  }
}
