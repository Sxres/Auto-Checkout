<script>
  import { onMount } from 'svelte'
  import Icon from '../../lib/Icon.svelte'
  import Modal from '../../lib/Modal.svelte'
  import ProductArt from '../../lib/ProductArt.svelte'
  import { recordingSupported, pickMimeType, startRecording } from '../../lib/record.js'
  import { createCapture, uploadCapture, getCapture } from '../../lib/capture.js'

  let { product, onclose, ondone } = $props()

  const STEPS = [
    {
      kind: 'train', label: 'Turn video', duration: 30, demo: 'turn',
      title: 'Rotate the product slowly',
      instruction: (name) => `Hold ${name} in one hand and turn it so every side faces the camera — top and bottom too.`,
      hint: 'Keep it centred and well lit. About 30 seconds.',
    },
    {
      kind: 'val', label: 'Other hand', duration: 15, demo: 'turn',
      title: 'Now use your other hand',
      instruction: (name) => `Switch ${name} to your other hand and turn it again, showing all sides.`,
      hint: 'A different hand gives the model variety. About 15 seconds.',
    },
    ...Array.from({ length: 5 }, (_, i) => ({
      kind: 'swipe', label: `Swipe ${i + 1}`, duration: 3, demo: 'swipe',
      title: 'Swipe it across',
      instruction: (name) => `Swipe ${name} across the frame once, like a customer checking out.`,
      hint: 'One smooth pass, about 3 seconds.',
    })),
  ]

  let phase = $state('brief') // brief | countdown | recording | review | upload | done
  let stepIndex = $state(0)
  let takes = $state(Array(STEPS.length).fill(null))
  let cameraState = $state('idle') // idle | starting | live | error
  let cameraError = $state('')
  let videoElement = $state()
  let videoSize = $state({ w: 0, h: 0 })
  let elapsed = $state(0)
  let count = $state(3)
  let confirmDiscard = $state(false)
  let clipStates = $state([])
  let uploadNote = $state('')

  const recorderOk = recordingSupported()
  let stream
  let mounted = false
  let recorder
  let recordTimer
  let countdownTimer
  let pollTimer
  let noteTimer
  let startedAt = 0
  let abortController

  const step = $derived(STEPS[stepIndex])
  const currentTake = $derived(takes[stepIndex])
  const keptCount = $derived(takes.filter(Boolean).length)
  const canRecord = $derived(cameraState === 'live' && recorderOk)
  const progress = $derived(Math.min(1, elapsed / step.duration))
  const isLastStep = $derived(stepIndex === STEPS.length - 1)

  const fmt = (s) => {
    const secs = Math.max(0, Math.floor(s))
    return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`
  }

  // --- Camera (lifecycle mirrors Kiosk.svelte; resolution ideals added) -------

  function stopCamera() {
    stream?.getTracks().forEach((track) => track.stop())
    stream = null
    if (videoElement) videoElement.srcObject = null
  }

  async function startCamera() {
    if (cameraState === 'starting' || cameraState === 'live') return
    cameraState = 'starting'
    cameraError = ''

    if (!navigator.mediaDevices?.getUserMedia) {
      cameraState = 'error'
      cameraError = window.isSecureContext
        ? 'This browser does not support camera access.'
        : 'Open this console over HTTPS or localhost to enable the camera.'
      return
    }

    try {
      const camera = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      if (!mounted) {
        camera.getTracks().forEach((track) => track.stop())
        return
      }
      stream = camera
      camera.getTracks().forEach((track) => {
        track.onended = () => {
          if (!mounted) return
          cameraState = 'error'
          cameraError = 'The camera stopped. Reconnect it and try again.'
          recorder?.cancel()
          clearInterval(recordTimer)
        }
      })
      videoElement.srcObject = camera
      await videoElement.play()
      if (mounted) cameraState = 'live'
    } catch (error) {
      if (!mounted) return
      stopCamera()
      cameraState = 'error'
      if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
        cameraError = 'Allow camera access in your browser, then try again.'
      } else if (error.name === 'NotFoundError') {
        cameraError = 'No camera was found. Connect one and try again.'
      } else if (error.name === 'NotReadableError' || error.name === 'AbortError') {
        cameraError = 'Your camera is in use or unavailable. Close other camera apps and try again.'
      } else {
        cameraError = 'We could not start your camera. Please try again.'
      }
    }
  }

  // --- Recording flow --------------------------------------------------------

  function beginCountdown() {
    if (!canRecord) return
    confirmDiscard = false
    phase = 'countdown'
    count = 3
    countdownTimer = setInterval(() => {
      count -= 1
      if (count <= 0) {
        clearInterval(countdownTimer)
        startTake()
      }
    }, 1000)
  }

  function cancelCountdown() {
    clearInterval(countdownTimer)
    phase = 'brief'
  }

  function startTake() {
    phase = 'recording'
    elapsed = 0
    startedAt = performance.now()
    recorder = startRecording(stream, { mimeType: pickMimeType() })
    // Timestamp-based elapsed: background-tab timer throttling can't shorten a clip.
    recordTimer = setInterval(() => {
      elapsed = (performance.now() - startedAt) / 1000
      if (elapsed >= step.duration) stopTake()
    }, 100)
  }

  async function stopTake() {
    if (phase !== 'recording') return
    clearInterval(recordTimer)
    const rec = recorder
    recorder = null
    const blob = await rec.stop()
    if (!mounted || !blob) return
    if (takes[stepIndex]?.url) URL.revokeObjectURL(takes[stepIndex].url)
    takes[stepIndex] = { blob, url: URL.createObjectURL(blob), duration: elapsed, size: blob.size }
    phase = 'review'
  }

  function reRecord() {
    if (takes[stepIndex]?.url) URL.revokeObjectURL(takes[stepIndex].url)
    takes[stepIndex] = null
    phase = 'brief'
  }

  function keepTake() {
    if (!isLastStep) {
      stepIndex += 1
      phase = 'brief'
    } else {
      startUpload()
    }
  }

  function prevStep() {
    if (stepIndex > 0) {
      stepIndex -= 1
      phase = takes[stepIndex] ? 'review' : 'brief'
    }
  }

  // --- Upload + annotation ---------------------------------------------------

  async function startUpload() {
    phase = 'upload'
    uploadNote = ''
    abortController = new AbortController()
    clipStates = STEPS.map((s) => ({
      kind: s.kind, label: s.label, status: 'pending', progress: 0, capture_id: null, frames: null, error: '',
    }))
    for (let i = 0; i < STEPS.length; i++) {
      if (!mounted) return
      await uploadClip(i)
    }
    if (mounted) startPolling()
    noteTimer = setTimeout(() => {
      if (mounted && phase === 'upload') uploadNote = 'Annotation is taking longer than usual — still processing.'
    }, 60000)
  }

  async function uploadClip(i) {
    const clip = clipStates[i]
    clip.status = 'uploading'
    clip.progress = 0
    clip.error = ''
    try {
      const capture = await createCapture(product.sku, STEPS[i].kind)
      if (!mounted) return
      clip.capture_id = capture.capture_id
      await uploadCapture(capture, takes[i].blob, {
        onProgress: (p) => {
          if (mounted) clip.progress = p
        },
        signal: abortController.signal,
      })
      if (!mounted) return
      clip.status = 'processing'
      clip.progress = 1
    } catch (err) {
      if (!mounted || err.code === 'aborted') return
      clip.status = 'error'
      clip.error = err.message ?? 'Upload failed.'
    }
  }

  async function retryClip(i) {
    await uploadClip(i)
    if (mounted && clipStates[i].status === 'processing') startPolling()
  }

  function startPolling() {
    clearInterval(pollTimer)
    pollTimer = setInterval(async () => {
      if (!mounted) return
      let allReady = true
      let anyProcessing = false
      for (const clip of clipStates) {
        if (clip.status === 'processing' && clip.capture_id) {
          anyProcessing = true
          try {
            const result = await getCapture(clip.capture_id)
            if (!mounted) return
            clip.status = result.status
            clip.frames = result.frames
          } catch {
            // A failed annotation stays "processing"; keep polling.
          }
        }
        if (clip.status !== 'ready') allReady = false
      }
      if (allReady) {
        clearInterval(pollTimer)
        finish()
      } else if (!anyProcessing) {
        // Only errored clips remain — wait for the user to retry.
        clearInterval(pollTimer)
      }
    }, 1000)
  }

  function finish() {
    phase = 'done'
    const totalLabelled = clipStates.reduce((sum, c) => sum + (c.frames?.labelled ?? 0), 0)
    ondone?.(totalLabelled)
  }

  // --- Close guard + cleanup -------------------------------------------------

  function requestClose() {
    const inProgress = phase === 'countdown' || phase === 'recording' || phase === 'upload' || keptCount > 0
    if (inProgress && phase !== 'done') {
      confirmDiscard = true
    } else {
      onclose?.()
    }
  }

  onMount(() => {
    mounted = true
    startCamera()
    return () => {
      mounted = false
      clearInterval(countdownTimer)
      clearInterval(recordTimer)
      clearInterval(pollTimer)
      clearTimeout(noteTimer)
      recorder?.cancel()
      abortController?.abort()
      stopCamera()
      for (const take of takes) if (take?.url) URL.revokeObjectURL(take.url)
    }
  })
</script>

<Modal title="Record product video" width={860} onclose={requestClose}>
  {#snippet footer()}
    {#if confirmDiscard}
      <!-- discard strip carries its own actions -->
    {:else if phase === 'brief'}
      <button class="btn-line modal-btn" onclick={requestClose}>Cancel</button>
      {#if stepIndex > 0}
        <button class="btn-line modal-btn" onclick={prevStep}>Previous step</button>
      {/if}
      <button class="btn-red modal-btn" disabled={!canRecord} onclick={beginCountdown}>
        <Icon name="video" size={15} /> Start recording
      </button>
    {:else if phase === 'countdown'}
      <button class="btn-line modal-btn" onclick={cancelCountdown}>Cancel</button>
    {:else if phase === 'recording'}
      <button class="btn-red modal-btn" disabled={elapsed < 1} onclick={stopTake}>
        <Icon name="stop" size={15} /> Stop
      </button>
    {:else if phase === 'review'}
      <button class="btn-line modal-btn" onclick={reRecord}>
        <Icon name="refresh" size={15} /> Re-record
      </button>
      <button class="btn-red modal-btn" onclick={keepTake}>
        <Icon name="check" size={15} /> {isLastStep ? 'Keep & upload' : 'Keep & continue'}
      </button>
    {:else if phase === 'upload'}
      <button class="btn-red modal-btn" disabled>Uploading…</button>
    {:else if phase === 'done'}
      <button class="btn-red modal-btn" onclick={onclose}>
        <Icon name="checkCircle" size={15} /> Back to catalog
      </button>
    {/if}
  {/snippet}

  {#if confirmDiscard}
    <div class="discard">
      <span class="icon-chip discard-icon"><Icon name="alert" size={18} /></span>
      <p class="discard-title">Discard this session?</p>
      <p class="discard-sub">Your recorded takes will be lost and you'll start over.</p>
      <div class="discard-actions">
        <button class="btn-line modal-btn" onclick={() => (confirmDiscard = false)}>Keep going</button>
        <button class="btn-red modal-btn" onclick={onclose}>Discard</button>
      </div>
    </div>
  {:else}
    <div class="wiz-head">
      <div class="wiz-product">
        <span class="wiz-thumb"><ProductArt kind={product.art} size={22} /></span>
        <div>
          <p class="wiz-name">{product.name}</p>
          <p class="wiz-sku tnum">{product.sku}</p>
        </div>
      </div>
      {#if cameraState === 'live' && videoSize.w}
        <span class="pill pill-gray res-chip tnum">{videoSize.w} × {videoSize.h}</span>
      {/if}
    </div>

    {#if !recorderOk}
      <div class="banner">
        <Icon name="alert" size={15} /> This browser can't record video. Use Chrome or Edge to capture footage.
      </div>
    {/if}

    {#if phase === 'upload' || phase === 'done'}
      <div class="clips">
        <p class="clips-head">
          {#if phase === 'done'}
            <Icon name="checkCircle" size={16} /> All 7 clips uploaded and annotated
          {:else}
            Uploading and annotating your clips…
          {/if}
        </p>
        {#each clipStates as clip, i}
          <div class="clip-row">
            <span class="pill clip-kind {clip.status === 'ready' ? 'pill-green' : clip.status === 'error' ? 'pill-amber' : 'pill-gray'}">{clip.kind}</span>
            <span class="clip-label">{clip.label}</span>
            {#if clip.status === 'uploading'}
              <span class="clip-bar"><span style="transform: scaleX({clip.progress})"></span></span>
              <span class="clip-status tnum">{Math.round(clip.progress * 100)}%</span>
            {:else if clip.status === 'processing'}
              <span class="clip-status muted">Annotating…</span>
            {:else if clip.status === 'ready'}
              <span class="clip-status green"><Icon name="check" size={13} /> {clip.frames?.labelled ?? 0} frames</span>
            {:else if clip.status === 'error'}
              <span class="clip-status amber">{clip.error}</span>
              <button class="btn-line clip-retry" onclick={() => retryClip(i)}>Retry</button>
            {:else}
              <span class="clip-status muted">Waiting…</span>
            {/if}
          </div>
        {/each}
        {#if uploadNote}<p class="clips-note">{uploadNote}</p>{/if}
      </div>
    {:else}
      <div class="stepper">
        {#each STEPS as s, i}
          <span
            class="step-dot"
            class:kept={takes[i]}
            class:current={i === stepIndex}
            title={s.label}
          >
            {#if takes[i]}<Icon name="check" size={13} />{:else}{i + 1}{/if}
          </span>
        {/each}
        <span class="step-count tnum">Step {stepIndex + 1} of {STEPS.length} · {keptCount} kept</span>
      </div>

      <div class="preview">
        <video
          class="feed"
          class:hidden={phase === 'review'}
          bind:this={videoElement}
          onloadedmetadata={() => (videoSize = { w: videoElement.videoWidth, h: videoElement.videoHeight })}
          autoplay
          muted
          playsinline
          aria-hidden="true"
        ></video>
        {#if phase === 'review' && currentTake}
          <video class="feed playback" src={currentTake.url} controls autoplay muted playsinline></video>
        {/if}

        {#if cameraState === 'error'}
          <div class="cam-overlay">
            <span class="icon-chip cam-icon"><Icon name="camera" size={18} /></span>
            <p class="cam-msg">{cameraError}</p>
            <button class="btn-red cam-retry" onclick={startCamera}>Retry</button>
          </div>
        {:else if cameraState !== 'live'}
          <div class="cam-overlay">
            <p class="cam-msg">Starting camera…</p>
          </div>
        {/if}

        {#if phase === 'countdown'}
          <div class="countdown tnum">{count}</div>
        {/if}
        {#if phase === 'recording'}
          <span class="rec-chip"><span class="dot rec-dot"></span> REC</span>
          <span class="timer tnum">{fmt(elapsed)} / {fmt(step.duration)}</span>
          <span class="rec-bar"><span style="transform: scaleX({progress})"></span></span>
        {/if}
      </div>

      <div class="brief">
        <div class="demo-stage demo-{step.demo}" aria-hidden="true">
          <ProductArt kind={product.art} size={40} />
        </div>
        <div class="brief-text">
          <p class="brief-title">{step.title}</p>
          <p class="brief-instruction">{step.instruction(product.name)}</p>
          <p class="brief-hint">{step.hint}</p>
        </div>
      </div>
    {/if}
  {/if}
</Modal>

<style>
  .modal-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 13px;
  }

  .wiz-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
  }
  .wiz-product {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .wiz-thumb {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: var(--chip);
    color: var(--ink);
  }
  .wiz-name {
    font-size: 15px;
    font-weight: 700;
  }
  .wiz-sku {
    font-size: 12px;
    color: var(--muted);
  }
  .res-chip {
    font-size: 11px;
  }

  .banner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    margin-bottom: 16px;
    border-radius: 8px;
    background: var(--amber-bg);
    color: var(--amber);
    font-size: 13px;
    font-weight: 600;
  }

  .stepper {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
  }
  .step-dot {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    background: var(--chip);
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    border: 2px solid transparent;
  }
  .step-dot.current {
    border-color: var(--red);
    color: var(--ink);
  }
  .step-dot.kept {
    background: var(--green-bg);
    color: var(--green);
  }
  .step-count {
    margin-left: auto;
    font-size: 12px;
    color: var(--muted);
  }

  .preview {
    position: relative;
    aspect-ratio: 16 / 9;
    max-height: 420px;
    width: 100%;
    border-radius: 12px;
    background: var(--cam);
    border: 1px solid var(--cam-border);
    overflow: hidden;
  }
  .feed {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .feed.hidden {
    display: none;
  }
  .playback {
    background: #000;
  }

  .cam-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 24px;
    text-align: center;
    background: var(--cam);
  }
  .cam-icon {
    background: var(--dark2);
    color: var(--white);
  }
  .cam-msg {
    color: var(--beige);
    font-size: 14px;
    max-width: 360px;
  }
  .cam-retry {
    height: 40px;
    padding: 0 22px;
    font-size: 13px;
  }

  .countdown {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-size: 96px;
    font-weight: 800;
    color: var(--white);
    background: rgba(23, 23, 23, 0.35);
    animation: fadeIn 0.15s ease both;
  }
  .rec-chip {
    position: absolute;
    top: 12px;
    left: 12px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 11px;
    border-radius: 999px;
    background: rgba(23, 23, 23, 0.6);
    color: var(--white);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }
  .rec-dot {
    color: var(--red);
    animation: pulse 1.2s ease-in-out infinite;
  }
  .timer {
    position: absolute;
    top: 12px;
    right: 12px;
    padding: 5px 11px;
    border-radius: 999px;
    background: rgba(23, 23, 23, 0.6);
    color: var(--white);
    font-size: 12px;
    font-weight: 700;
  }
  .rec-bar {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 4px;
    background: rgba(255, 255, 255, 0.18);
  }
  .rec-bar > span {
    display: block;
    height: 100%;
    background: var(--red);
    transform-origin: left;
  }

  .brief {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 18px;
  }
  .demo-stage {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 72px;
    height: 72px;
    border-radius: 12px;
    background: var(--chip);
    color: var(--ink);
    overflow: hidden;
  }
  .demo-turn :global(svg) {
    animation: spin 4s linear infinite;
  }
  .demo-swipe :global(svg) {
    animation: swipe 1.6s ease-in-out infinite;
  }
  .brief-title {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 3px;
  }
  .brief-instruction {
    font-size: 13px;
    color: var(--ink);
    line-height: 1.45;
  }
  .brief-hint {
    font-size: 12px;
    color: var(--muted);
    margin-top: 4px;
  }

  .clips-head {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--green);
  }
  .clip-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px solid var(--border);
  }
  .clip-row:last-child {
    border-bottom: none;
  }
  .clip-kind {
    font-size: 11px;
    min-width: 52px;
    justify-content: center;
  }
  .clip-label {
    font-size: 13px;
    font-weight: 600;
    min-width: 84px;
  }
  .clip-bar {
    flex: 1;
    height: 6px;
    border-radius: 999px;
    background: var(--chip);
    overflow: hidden;
  }
  .clip-bar > span {
    display: block;
    height: 100%;
    background: var(--red);
    transform-origin: left;
    transition: transform 0.15s ease;
  }
  .clip-status {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-left: auto;
    font-size: 12px;
    font-weight: 600;
  }
  .clip-status.muted {
    color: var(--muted);
  }
  .clip-status.green {
    color: var(--green);
  }
  .clip-status.amber {
    color: var(--amber);
  }
  .clip-retry {
    height: 30px;
    padding: 0 14px;
    font-size: 12px;
  }
  .clips-note {
    margin-top: 14px;
    font-size: 12px;
    color: var(--muted);
  }

  .discard {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 24px 0 8px;
    animation: fadeUp 0.2s ease both;
  }
  .discard-icon {
    background: var(--amber-bg);
    color: var(--amber);
    margin-bottom: 14px;
  }
  .discard-title {
    font-size: 16px;
    font-weight: 700;
  }
  .discard-sub {
    font-size: 13px;
    color: var(--muted);
    margin-top: 4px;
  }
  .discard-actions {
    display: flex;
    gap: 12px;
    margin-top: 22px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @keyframes swipe {
    0%, 100% {
      transform: translateX(-45%);
    }
    50% {
      transform: translateX(45%);
    }
  }
</style>