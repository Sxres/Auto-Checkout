// MediaRecorder wrapper for the guided capture flow. Pure browser module — no
// Svelte imports. The caller owns the camera stream; recording never stops its
// tracks, because one stream is shared across all seven takes in a session.

const MIME_CANDIDATES = ['video/webm;codecs=vp8', 'video/webm', 'video/mp4']

export function pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return ''
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

export function recordingSupported() {
  return pickMimeType() !== ''
}

export function extFor(mime) {
  return mime.includes('mp4') ? 'mp4' : 'webm'
}

export function startRecording(stream, { mimeType = pickMimeType(), videoBitsPerSecond = 2_500_000 } = {}) {
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType, videoBitsPerSecond } : { videoBitsPerSecond })
  const chunks = []
  let discarded = false
  let settled = false
  let resolveStop
  let rejectStop

  const stopPromise = new Promise((resolve, reject) => {
    resolveStop = resolve
    rejectStop = reject
  })

  const cleanup = () => {
    recorder.ondataavailable = null
    recorder.onstop = null
    recorder.onerror = null
  }

  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) chunks.push(event.data)
  }
  recorder.onstop = () => {
    if (settled) return
    settled = true
    cleanup()
    if (discarded) {
      resolveStop(null)
      return
    }
    resolveStop(new Blob(chunks, { type: recorder.mimeType || mimeType || 'video/webm' }))
  }
  recorder.onerror = (event) => {
    if (settled) return
    settled = true
    cleanup()
    rejectStop(event.error ?? new Error('Recording failed.'))
  }

  // Timeslice chunks keep memory bounded and survive a mid-take crash; only the
  // first chunk carries the WebM header, so concatenating them is a valid clip.
  recorder.start(250)

  return {
    mimeType: recorder.mimeType || mimeType,
    stop() {
      if (recorder.state !== 'inactive') recorder.stop()
      return stopPromise
    },
    cancel() {
      discarded = true
      if (recorder.state !== 'inactive') recorder.stop()
      return stopPromise
    },
  }
}