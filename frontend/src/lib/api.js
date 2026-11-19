// Backend integration stubs. Each function is one future API call — replace the
// body with a real fetch once the backend exists. The return shapes are the
// contract the UI consumes; keep them stable when wiring real data.

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class RecognizeError extends Error {
  constructor(code, message) {
    super(message)
    this.code = code
  }
}

export async function fetchProducts() {
  // [{ sku, name, category, photos, status: 'Ready' | 'Needs images', art, thumb, price }]
  return []
}

export async function fetchReviewQueue() {
  // [{ id, capture, label, suggested, match, time, art }]
  return []
}

export async function fetchVersions() {
  // [{ v, created, images, rate, status: 'Live' | 'Archived' }]
  return []
}

export async function fetchDataset() {
  // { scans } — reviewed scans available as training data
  return { scans: 0 }
}

export async function fetchOverview() {
  return {
    checkoutsToday: 0,
    recognitionRate: null, // e.g. '96.8%' once measured
    avgCheckoutSeconds: null,
    correctedToday: 0,
    chart: { labels: [], heights: [] }, // one height per time bucket
    checkouts: [], // [{ id, time, items, duration, status }]
  }
}

export async function fetchMonitoring() {
  // null = no telemetry yet. alerts: [{ id, title, desc, source, detected, status }]
  return {
    kiosk: { cameraConnected: null, failures24h: null },
    api: { healthy: null, latencyMs: null, errorRate: null },
    model: { ready: null, latencyMs: null, lowConfidenceRate: null },
    alerts: [],
  }
}

export async function fetchKioskStatus() {
  return { online: false, cameraConnected: false, lastCheck: null }
}

export async function recognizeItems(frame) {
  // items: [{ key, name, price, art }]
  // detections: [{ label, x, y, w, h }] — box coords in % of the uploaded frame
  const body = new FormData()
  body.append('file', frame, 'frame.jpg')

  let response
  try {
    response = await fetch(`${API_URL}/recognize`, { method: 'POST', body })
  } catch {
    throw new RecognizeError('network', 'Could not reach the recognition service.')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
    throw new RecognizeError(detail?.code ?? 'unknown', detail?.message ?? 'Recognition failed.')
  }
  if (!Array.isArray(payload?.items) || !Array.isArray(payload?.detections)) {
    throw new RecognizeError('invalid_response', 'The recognition service returned an unexpected response.')
  }
  return payload
}
