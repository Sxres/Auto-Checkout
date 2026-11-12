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
  detections: [], // { label, x, y, w, h } in % of the video area
  phase: 'empty', // empty | recognizing | items
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
  go('kiosk')
}

export async function recognize() {
  if (app.phase !== 'empty') return
  app.phase = 'recognizing'
  const [result] = await Promise.all([
    api.recognizeItems(),
    new Promise((r) => setTimeout(r, 1700)),
  ])
  app.detections = result.detections
  if (!result.items.length) {
    app.phase = 'empty'
    toast('Nothing recognized — the recognition service is not connected yet.')
    return
  }
  app.cart = result.items.map((i) => ({ ...i, qty: 1 }))
  app.phase = 'items'
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
}
