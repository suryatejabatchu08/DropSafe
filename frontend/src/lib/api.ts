// Frontend API utilities
// All API calls to FastAPI backend

import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Dashboard endpoints
export async function getDashboardStats() {
  try {
    const response = await api.get("/dashboard/stats");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch dashboard stats:", error);
    return null;
  }
}

export async function getActiveTriggers() {
  try {
    const response = await api.get("/triggers/active");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch triggers:", error);
    return null;
  }
}

export async function getDailyClaimsSummary() {
  try {
    // Route is at /dashboard/claims/daily-summary (dashboard router prefix)
    const response = await api.get("/dashboard/claims/daily-summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch claims summary:", error);
    return null;
  }
}

export async function getDailyPayoutsSummary() {
  try {
    const response = await api.get("/payouts/daily-summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch payouts summary:", error);
    return null;
  }
}

// Zones endpoints
export async function getZonesSummary() {
  try {
    const response = await api.get("/zones/summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch zones summary:", error);
    return null;
  }
}

export async function getZones() {
  try {
    const response = await api.get("/premium/zones");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch zones:", error);
    return null;
  }
}

export async function getTriggerHistory(days = 30) {
  try {
    const response = await api.get(`/triggers/zone/history?days=${days}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch trigger history:", error);
    return null;
  }
}

// Claims endpoints
export async function getReviewQueue() {
  try {
    const response = await api.get("/fraud/claims/review");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch review queue:", error);
    return null;
  }
}

export async function approveClaim(claimId: string) {
  try {
    const response = await api.post(`/fraud/claims/${claimId}/approve`, {});
    return response.data;
  } catch (error) {
    console.error("Failed to approve claim:", error);
    return null;
  }
}

export async function rejectClaim(claimId: string, reason: string) {
  try {
    const response = await api.post(`/fraud/claims/${claimId}/reject`, {
      reason,
    });
    return response.data;
  } catch (error) {
    console.error("Failed to reject claim:", error);
    return null;
  }
}

export async function getFraudAlerts() {
  try {
    const response = await api.get("/fraud/alerts");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch fraud alerts:", error);
    return null;
  }
}

// Payouts endpoints
export async function getPayoutSummary() {
  try {
    const response = await api.get("/payouts/summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch payout summary:", error);
    return null;
  }
}

export async function getWorkerPayouts(workerId: string) {
  try {
    const response = await api.get(`/payouts/worker/${workerId}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch worker payouts:", error);
    return null;
  }
}

export async function retryPayout(payoutId: string) {
  try {
    const response = await api.post(`/payouts/retry/${payoutId}`, {});
    return response.data;
  } catch (error) {
    console.error("Failed to retry payout:", error);
    return null;
  }
}

export async function getRecentPayouts() {
  try {
    const response = await api.get("/payouts/summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch recent payouts:", error);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Worker Dashboard
// ─────────────────────────────────────────────────────────────────────────────

export async function getWorkerDashboard(workerId: string) {
  try {
    const response = await api.get(`/worker/${workerId}/dashboard`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch worker dashboard:", error);
    return null;
  }
}

export async function getWorkerHistory(workerId: string, page = 1, limit = 10) {
  try {
    const response = await api.get(`/worker/${workerId}/history`, {
      params: { page, limit },
    });
    return response.data;
  } catch (error) {
    console.error("Failed to fetch worker history:", error);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Analytics
// ─────────────────────────────────────────────────────────────────────────────

export async function getLossRatio(period = "current_week") {
  try {
    const response = await api.get("/analytics/loss-ratio", { params: { period } });
    return response.data;
  } catch (error) {
    console.error("Failed to fetch loss ratio:", error);
    return null;
  }
}

export async function getPredictiveAnalytics() {
  try {
    const response = await api.get("/analytics/predictive");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch predictive analytics:", error);
    return [];
  }
}

export async function getFraudSummary() {
  try {
    const response = await api.get("/analytics/fraud-summary");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch fraud summary:", error);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — ML
// ─────────────────────────────────────────────────────────────────────────────

export async function getMLModelStatus() {
  try {
    const response = await api.get("/ml/model/status");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch ML model status:", error);
    return null;
  }
}

export async function triggerMLRetrain() {
  try {
    const response = await api.post("/ml/train");
    return response.data;
  } catch (error) {
    console.error("Failed to trigger ML retrain:", error);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — Zones (for demo page)
// ─────────────────────────────────────────────────────────────────────────────

export default api;
