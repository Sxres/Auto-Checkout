// Capture service client for the guided capture flow (issue #18). Mirrors the
// API contract documented in ml/README.md (implemented server-side in #14):
//
//   GET  /products          -> catalog products
//   POST /captures {sku,kind} -> {capture_id, upload:{url, fields, expires_in}}
//   GET  /captures/{id}     -> {capture_id, sku, kind, status, frames}
//   GET  /captures?sku=     -> that product's captures
//
// kind = train|val|swipe; status = awaiting_upload|processing|ready. A failed
// annotation stays "processing" (its error is in the logs) — there is no
// "failed" API status. frames = {sampled, labelled}, null before ready; a swipe
// manifest has labelled: 0.
//
// Set VITE_CAPTURE_API_URL to talk to the real #14 backend. Unset, an in-browser
// mock simulates the whole contract so the flow is demonstrable now. The mock
// lives in a module-level Map: it survives closing the modal but resets on page
// reload. The real API persists server-side.
//
// Catalog seam: the mock validates SKUs against the UI catalog (app.products,
// PRD-xxx). The real GET /products returns backend/app/catalog.json (COKE-330,
// ...). When #14 lands, wire fetchProducts() to the capture API so both converge.

import { app } from './state.svelte.js'
import { extFor } from './record.js'

const CAPTURE_URL = import.meta.env.VITE_CAPTURE_API_URL
const KINDS = ['train', 'val', 'swipe']

export class CaptureError extends Error {
  constructor(code, message) {
    super(message)
    this.code = code
  }
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// --- Mock implementation -----------------------------------------------------

const store = new Map()

const mockFrames = (kind) =>
  kind === 'train' ? { sampled: 90, labelled: 88 } : kind === 'val' ? { sampled: 45, labelled: 44 } : { sampled: 9, labelled: 0 }

const mock = {
  async fetchCaptureProducts() {
    return app.products.map((p) => ({ sku: p.sku, name: p.name, category: p.category, price: p.price }))
  },

  async createCapture(sku, kind) {
    if (!KINDS.includes(kind)) throw new CaptureError('invalid_kind', `Unknown capture kind "${kind}".`)
    if (!app.products.some((p) => p.sku === sku)) throw new CaptureError('invalid_sku', `SKU "${sku}" is not in the catalog.`)
    await delay(150)
    const capture_id = crypto.randomUUID().replaceAll('-', '')
    const record = { capture_id, sku, kind, status: 'awaiting_upload', frames: null, blob: null, readyAt: null }
    store.set(capture_id, record)
    return {
      capture_id,
      upload: {
        url: 'https://mock-capture.local/upload',
        fields: {
          key: `raw/${capture_id}/source.webm`,
          'Content-Type': 'video/webm',
          policy: 'mock',
          'x-amz-signature': 'mock',
        },
        expires_in: 300,
      },
    }
  },

  async uploadCapture(capture, blob, { onProgress, signal } = {}) {
    const record = store.get(capture.capture_id)
    if (!record) throw new CaptureError('not_found', 'Capture not found.')
    const ticks = 10
    for (let i = 1; i <= ticks; i++) {
      if (signal?.aborted) throw new CaptureError('aborted', 'Upload cancelled.')
      await delay(120)
      onProgress?.(i / ticks)
    }
    if (signal?.aborted) throw new CaptureError('aborted', 'Upload cancelled.')
    record.blob = blob
    record.status = 'processing'
    // Compressed stand-in for the real annotator (~25-60 s per video).
    record.readyAt = Date.now() + 4000
  },

  async getCapture(id) {
    const record = store.get(id)
    if (!record) throw new CaptureError('not_found', 'Capture not found.')
    if (record.status === 'processing' && record.readyAt && Date.now() >= record.readyAt) {
      record.status = 'ready'
      record.frames = mockFrames(record.kind)
    }
    const { capture_id, sku, kind, status, frames } = record
    return { capture_id, sku, kind, status, frames }
  },

  async listCaptures(sku) {
    return [...store.values()]
      .filter((r) => r.sku === sku)
      .map(({ capture_id, sku: s, kind, status, frames }) => ({ capture_id, sku: s, kind, status, frames }))
  },
}

// --- HTTP implementation (dormant until #14 deploys) -------------------------

async function request(path, options) {
  let response
  try {
    response = await fetch(`${CAPTURE_URL}${path}`, options)
  } catch {
    throw new CaptureError('network', 'Could not reach the capture service.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
    throw new CaptureError(detail?.code ?? 'unknown', detail?.message ?? 'Capture request failed.')
  }
  return payload
}

const http = {
  fetchCaptureProducts() {
    return request('/products')
  },

  createCapture(sku, kind) {
    return request('/captures', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sku, kind }),
    })
  },

  getCapture(id) {
    return request(`/captures/${id}`)
  },

  listCaptures(sku) {
    return request(`/captures?sku=${encodeURIComponent(sku)}`)
  },

  // Presigned S3 POST. XMLHttpRequest is the only way to report real upload
  // progress (fetch cannot). Fields go first, then the file, per the S3 POST contract.
  uploadCapture(capture, blob, { onProgress, signal } = {}) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const form = new FormData()
      for (const [key, value] of Object.entries(capture.upload.fields)) form.append(key, value)
      form.append('file', blob, `source.${extFor(blob.type)}`)

      const onAbort = () => xhr.abort()
      signal?.addEventListener('abort', onAbort, { once: true })

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(event.loaded / event.total)
      }
      xhr.onload = () => {
        signal?.removeEventListener('abort', onAbort)
        if (xhr.status === 201 || xhr.status === 204 || xhr.status === 200) {
          onProgress?.(1)
          resolve()
        } else {
          reject(new CaptureError('upload_failed', `Upload failed (${xhr.status}).`))
        }
      }
      xhr.onerror = () => {
        signal?.removeEventListener('abort', onAbort)
        reject(new CaptureError('network', 'Could not reach the upload endpoint.'))
      }
      xhr.onabort = () => {
        signal?.removeEventListener('abort', onAbort)
        reject(new CaptureError('aborted', 'Upload cancelled.'))
      }
      xhr.open('POST', capture.upload.url)
      xhr.send(form)
    })
  },
}

const impl = CAPTURE_URL ? http : mock

export const fetchCaptureProducts = (...args) => impl.fetchCaptureProducts(...args)
export const createCapture = (...args) => impl.createCapture(...args)
export const uploadCapture = (...args) => impl.uploadCapture(...args)
export const getCapture = (...args) => impl.getCapture(...args)
export const listCaptures = (...args) => impl.listCaptures(...args)