// Where the API lives:
//   - VITE_API_URL at build time, if set (e.g. dashboard on Vercel, API elsewhere)
//   - the Vite dev server (npm run dev) -> http://127.0.0.1:8000
//   - otherwise the same origin (dashboard served by the API itself: Docker, desktop app)
const envUrl = import.meta.env.VITE_API_URL;
export const API_BASE_URL = (
  envUrl ? envUrl : import.meta.env.DEV ? 'http://127.0.0.1:8000' : window.location.origin
).replace(/\/$/, '');

// Optional: only needed when the API runs with FRAUD_API_KEY set
const API_KEY = import.meta.env.VITE_API_KEY || '';

export const WS_URL =
  (import.meta.env.VITE_WS_URL || `${API_BASE_URL.replace(/^http/, 'ws')}/ws/live`) +
  (API_KEY ? `?api_key=${encodeURIComponent(API_KEY)}` : '');

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
      ...(options.headers || {}),
    },
  });
  let body = null;
  try {
    body = await response.json();
  } catch {
    // non-JSON error page
  }
  if (!response.ok) {
    const detail = body && body.detail;
    // FastAPI 422s return a list of {loc, msg}; turn it into readable text
    const message = Array.isArray(detail)
      ? detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
      : detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body;
}

const json = (method, body) => ({ method, body: JSON.stringify(body) });

const fraudAPI = {
  checkHealth: () => request('/health'),
  getStats: () => request('/api/v1/stats'),
  getModelInfo: () => request('/api/v1/model/info'),
  getMonitoring: () => request('/api/v1/monitoring'),
  getRecent: ({ limit = 50, flaggedOnly = false, unlabeledOnly = false } = {}) =>
    request(`/api/v1/predictions/recent?limit=${limit}&flagged_only=${flaggedOnly}&unlabeled_only=${unlabeledOnly}`),
  predictFraud: (transaction) => request('/api/v1/predict', json('POST', transaction)),
  sendFeedback: (predictionId, isFraud) =>
    request(`/api/v1/predictions/${predictionId}/feedback`, json('POST', { is_fraud: isFraud })),
  getPolicy: () => request('/api/v1/settings/decision'),
  setPolicy: (reviewThreshold, declineThreshold) =>
    request('/api/v1/settings/decision', json('PUT', {
      review_threshold: reviewThreshold,
      decline_threshold: declineThreshold,
    })),
  retrain: () => request('/api/v1/model/retrain', { method: 'POST' }),
  getRetrainStatus: () => request('/api/v1/model/retrain'),
};

/** Python's weekday convention (0 = Monday ... 6 = Sunday), which the API uses.
 *  JS Date.getDay() is 0 = Sunday. */
export const apiDayOfWeek = (date = new Date()) => (date.getDay() + 6) % 7;

export default fraudAPI;
