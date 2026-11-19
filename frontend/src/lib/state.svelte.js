import * as api from './api.js'

const KEY = 'avc-console-v1'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) ?? {}
  } catch {
    return {}
  }
}
const saved = load()

export const app = $state({
  view: 'landing', // landing | manager | kiosk | complete
  page: 'overview', // overview | review | catalog | retraining | monitoring | settings

  kioskName: saved.kioskName ?? 'Kiosk 01',
  pin: saved.pin ?? '', // empty = any 6-digit PIN opens the console until one is set
  settings: {
    cameraSource: 'Camera 01: Integrated webcam',
    quality: '1080p · 30 fps',
    autoStart: true,
    askHelp: true,
    useCorrections: true,
    retention: '30 days',
    lockAfter: '5 minutes',
    ...(saved.settings ?? {}),
  },

  products: [],
  review: [],
  correctedToday: 0,
  versions: [],
  training: null, // { progress: 0..1 } while a run is in flight
  dataset: { scans: 0 },
  catalogImagesRequest: 0,

  checkouts: [],
  metrics: {
    checkoutsToday: 0,
    recognitionRate: null,
    avgCheckoutSeconds: null,
    chart: { labels: [], heights: [] },
  },
  monitoring: null,
  alerts: [],
  kioskStatus: { online: false, cameraConnected: false, lastCheck: null },

  cart: [], // { key, name, price, art, qty }
  detections: [], // { label, x, y, w, h } in % of the camera frame
  phase: 'empty', // empty | items
  modal: null, // review | help | startover
  lastTotal: 0,

  toast: null, // { message, action?, onAction? }
})

let workspaceLoaded = false
export async function loadWorkspace() {
  if (workspaceLoaded) return
  workspaceLoaded = true
  const [products, review, versions, dataset, overview, monitoring, kioskStatus] = await Promise.all([
    api.fetchProducts(),
    api.fetchReviewQueue(),
    api.fetchVersions(),
    api.fetchDataset(),
    api.fetchOverview(),
    api.fetchMonitoring(),
    api.fetchKioskStatus(),
  ])
  app.products = products
  app.review = review
  app.versions = versions
  app.dataset = dataset
  app.checkouts = overview.checkouts
  app.correctedToday = overview.correctedToday
  app.metrics = {
    checkoutsToday: overview.checkoutsToday,
    recognitionRate: overview.recognitionRate,
    avgCheckoutSeconds: overview.avgCheckoutSeconds,
    chart: overview.chart,
  }
  app.monitoring = monitoring
  app.alerts = monitoring.alerts
  app.kioskStatus = kioskStatus
}

export function persist() {
  localStorage.setItem(
    KEY,
    JSON.stringify({ kioskName: app.kioskName, pin: app.pin, settings: app.settings }),
  )
}

export function go(view, page) {
  app.view = view
  if (page) app.page = page
  app.modal = null
}

let toastTimer
export function toast(message, action) {
  clearTimeout(toastTimer)
  app.toast = { message, action }
  toastTimer = setTimeout(() => (app.toast = null), 4200)
}
export function dismissToast() {
  clearTimeout(toastTimer)
  app.toast = null
}

let trainTimer
export function startTraining() {
  if (app.training) return
  app.training = { progress: 0 }
  clearInterval(trainTimer)
  trainTimer = setInterval(() => {
    app.training.progress = Math.min(1, app.training.progress + 0.04)
    if (app.training.progress >= 1) {
      clearInterval(trainTimer)
      const minor = app.versions.length
        ? Math.max(...app.versions.map((v) => parseInt(v.v.split('.')[1], 10))) + 1
        : 0
      const images = app.dataset.scans + app.products.reduce((n, p) => n + p.photos, 0)
      app.training = {
        progress: 1,
        v: `v1.${minor}`,
        images: images.toLocaleString('en-US'),
        rate: '—',
      }
    }
  }, 160)
}

export function publishVersion() {
  const t = app.training
  if (!t || t.progress < 1) return
  for (const v of app.versions) if (v.status === 'Live') v.status = 'Archived'
  app.versions.unshift({ v: t.v, created: 'Just now', images: t.images, rate: t.rate, status: 'Live' })
  app.training = null
  toast(`Published ${t.v} to ${app.kioskName}.`)
}

export const cartCount = () => app.cart.reduce((n, i) => n + i.qty, 0)
export const cartTotal = () => app.cart.reduce((n, i) => n + i.qty * i.price, 0)

export function startCheckout() {
  app.cart = []
  app.detections = []
  app.phase = 'empty'
  resetSwipe()
  go('kiosk')
}

const SCAN_ERRORS = {
  model_unavailable: 'Recognition is offline — the model is not loaded. Please ask staff for help.',
  network: 'Could not reach the recognition service. Check the connection and try again.',
  invalid_response: 'The recognition service returned an unexpected response. Please try again.',
  invalid_image: 'The camera frame could not be read. Please try scanning again.',
  unsupported_media_type: 'The camera frame could not be read. Please try scanning again.',
  image_too_large: 'The camera frame was too large. Please try scanning again.',
}

// Mirrors ml/scripts/evaluate.py swipe scoring: each frame's top box adds its confidence
// to its class, and the highest total wins. Lower VOTE_TO_ADD charges sooner but leans
// on fewer agreeing frames.
const VOTE_TO_ADD = 1.5
// Time-based, not frame-count-based, so re-arming does not speed up with the poll rate
// and a brief detection dropout cannot charge the same item twice.
const REARM_EMPTY_MS = 450

let votes = new Map()
let emptySince = null
let charged = false
let observing = false
let lastError = null

function resetSwipe() {
  votes.clear()
  emptySince = null
  charged = false
  lastError = null
}

function addToBasket(item) {
  const existing = app.cart.find((i) => i.key === item.key)
  if (existing) existing.qty += 1
  else app.cart.push({ ...item, qty: 1 })
  app.phase = 'items'
}

export async function observe(frame) {
  if (observing) return
  observing = true
  try {
    const result = await api.recognizeItems(frame)
    lastError = null
    app.detections = result.detections
    const top = result.items[0]

    if (!top) {
      emptySince ??= performance.now()
      // The item has left the frame, so the next swipe can be charged.
      if (performance.now() - emptySince >= REARM_EMPTY_MS) {
        votes.clear()
        charged = false
      }
      return
    }

    emptySince = null
    if (charged) return

    votes.set(top.key, (votes.get(top.key) ?? 0) + result.detections[0].confidence)
    const leader = [...votes.entries()].reduce((a, b) => (b[1] > a[1] ? b : a))
    if (leader[1] >= VOTE_TO_ADD) {
      addToBasket(top)
      charged = true
      votes.clear()
    }
  } catch (error) {
    app.detections = []
    // Polling repeats several times a second; only announce a change of failure.
    if (lastError !== error.code) {
      lastError = error.code
      toast(SCAN_ERRORS[error.code] ?? 'Recognition failed. Retrying…')
    }
  } finally {
    observing = false
  }
}

export function setQty(key, delta) {
  const item = app.cart.find((i) => i.key === key)
  if (!item) return
  item.qty += delta
  if (item.qty <= 0) removeItem(key)
}

export function removeItem(key) {
  app.cart = app.cart.filter((i) => i.key !== key)
  if (app.cart.length === 0) app.phase = 'empty'
}

export function confirmCheckout() {
  app.lastTotal = cartTotal()
  app.modal = null
  go('complete')
}

export function clearBasket() {
  app.cart = []
  app.detections = []
  app.phase = 'empty'
  app.modal = null
  resetSwipe()
}
