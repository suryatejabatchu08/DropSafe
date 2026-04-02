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
    const response = await api.get("/claims/daily-summary");
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

export default api;
