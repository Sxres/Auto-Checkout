<script>
  import { onMount } from 'svelte'
  import Icon from '../../lib/Icon.svelte'
  import Mascot from '../../lib/Mascot.svelte'
  import ProductArt from '../../lib/ProductArt.svelte'
  import HelpChat from './HelpChat.svelte'
  import {
    app,
    go,
    cartCount,
    cartTotal,
    setQty,
    removeItem,
    confirmCheckout,
    clearBasket,
  } from '../../lib/state.svelte.js'
  import { money } from '../../lib/data.js'
  import { focusDialog } from '../../lib/dialog.js'

  let videoElement = $state()
  let cameraState = $state('idle')
  let cameraError = $state('')
  let stream
  let mounted = false

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
        : 'Open this checkout over HTTPS or localhost to enable the camera.'
      return
    }

    try {
      const camera = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      if (!mounted) {
        camera.getTracks().forEach((track) => track.stop())
        return
      }
      stream = camera
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

  onMount(() => {
    mounted = true
    if (app.settings.autoStart) startCamera()
    return () => {
      mounted = false
      stopCamera()
    }
  })

  const count = $derived(cartCount())
  const total = $derived(cartTotal())
  const statusText = $derived.by(() => {
    if (cameraState === 'starting') return 'Connecting to your camera…'
    if (cameraState === 'error') return 'Camera unavailable. Check access and try again.'
    if (cameraState === 'idle') return 'Start the camera to begin your checkout.'
    if (app.phase === 'items') return `${count} item${count === 1 ? '' : 's'} recognized. Ready for your next item.`
    if (app.phase === 'recognizing') return 'Recognizing your items…'
    return null
  })

  $effect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') app.modal = null
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
</script>

<div class="kiosk">
  <!-- Full-bleed camera -->
  <div class="video" class:live={cameraState === 'live'}>
    <video
      class="camera-feed"
      bind:this={videoElement}
      autoplay
      muted
      playsinline
      aria-hidden="true"
    ></video>
    {#if app.phase === 'items'}
      {#each app.detections as d, i}
        <div
          class="det-box"
          style="left: {d.x}%; top: {d.y}%; width: {d.w}%; height: {d.h}%; animation-delay: {i * 0.12}s"
        ></div>
        <span class="det-chip" style="left: {d.x}%; top: calc({d.y}% - 27px); animation-delay: {i * 0.12}s">
          {d.label}
        </span>
      {/each}
      <div class="corner-buddy">
        <Mascot dark mood="happy" size={13} />
      </div>
    {:else if cameraState !== 'live' || app.phase === 'recognizing'}
      <div class="video-overlay">
        {#if cameraState !== 'live'}
          <Mascot
            dark
            mood={cameraState === 'error' ? 'oops' : 'idle'}
            size={17}
            bubble={cameraState === 'idle' ? "Hi, I'm Byte! Start the camera and I'll spot your items." : ''}
          />
          <p class="video-title">
            {cameraState === 'starting' ? 'Starting camera…' : cameraState === 'error' ? 'Camera unavailable.' : 'Camera is off.'}
          </p>
          <p class="video-sub">
            {cameraState === 'error'
              ? cameraError
              : cameraState === 'starting'
                ? 'Allow camera access in your browser to see the live preview.'
                : 'Start the camera to see your items here.'}
          </p>
          {#if cameraState === 'idle' || cameraState === 'error'}
            <button class="btn-red start-cam" onclick={startCamera}>
              <Icon name="camera" size={16} />
              {cameraState === 'idle' ? 'Start camera' : 'Retry camera'}
            </button>
          {/if}
        {:else}
          <div class="scanline"></div>
          <Mascot dark mood="scan" size={15} />
          <p class="video-title">Recognizing your items…</p>
          <p class="video-sub">Keep your items still for a moment.</p>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Floating camera chip -->
  <div class="top-chip">
    <Icon name="camera" size={13} />
    <h1 class="kiosk-name">{app.kioskName}</h1>
    <span class="cam-state" role="status">
      <span
        class="dot"
        class:dot-live={cameraState === 'live'}
        class:dot-starting={cameraState === 'starting'}
      ></span>
      {cameraState === 'live' ? 'Live' : cameraState === 'starting' ? 'Connecting…' : 'Camera off'}
    </span>
  </div>

  <!-- Quick actions -->
  <div class="mini-actions">
    <button class="mini-btn" onclick={() => (app.modal = 'startover')}>Start over</button>
    <button class="mini-btn" onclick={() => go('landing')}>Staff access</button>
  </div>

  <!-- Basket + help -->
  <div class="side">
    <div class="card cart">
      <div class="cart-head">
        <span class="cart-title">Your items</span>
        <span class="cart-count tnum">{count} item{count === 1 ? '' : 's'}</span>
      </div>

      {#if app.cart.length > 0}
        <div class="cart-items">
          {#each app.cart as item, i (item.key)}
            <div class="cart-row" style="animation-delay: {i * 0.05}s">
              <span class="cart-thumb"><ProductArt kind={item.art} size={24} /></span>
              <span class="cart-name">{item.name}</span>
              <span class="cart-price tnum">{money(item.price * item.qty)}</span>
              <button class="step-btn minus" onclick={() => setQty(item.key, -1)} aria-label="Decrease {item.name}">−</button>
              <span class="cart-qty tnum">{item.qty}</span>
              <button class="step-btn plus" onclick={() => setQty(item.key, 1)} aria-label="Increase {item.name}">+</button>
              <button class="remove-btn" onclick={() => removeItem(item.key)}>Remove</button>
            </div>
          {/each}
        </div>
      {:else}
        <div class="empty-state cart-empty">
          <p class="empty-title">Your basket is empty.</p>
          <p class="empty-sub">Recognized items will appear here.</p>
        </div>
      {/if}

      <div class="total-row">
        <span class="total-label">Total</span>
        {#key total}
          <span class="total-value tnum">{money(total)}</span>
        {/key}
      </div>
      <button
        class="btn-red finish-btn"
        class:waiting={app.cart.length === 0}
        disabled={app.cart.length === 0}
        onclick={() => (app.modal = 'review')}
      >
        {app.cart.length === 0 ? 'Waiting for items' : 'Review & finish'}
      </button>
    </div>

    <button
      class="help-btn"
      class:open={app.modal === 'help'}
      aria-expanded={app.modal === 'help'}
      onclick={() => (app.modal = app.modal === 'help' ? null : 'help')}
    >
      <span class="help-icon"><Icon name="help" size={17} /></span>
      <span class="help-label">Need help?</span>
    </button>
  </div>

  <!-- Status pill -->
  {#if statusText}
    <div class="status-pill" class:busy={app.phase === 'recognizing'} class:done={app.phase === 'items'}>
      <span class="status-icon" class:spin={app.phase === 'recognizing'}>
        <Icon name={app.phase === 'items' ? 'checkCircle' : app.phase === 'recognizing' ? 'refresh' : 'scan'} size={16} />
      </span>
      <span class="status-text">{statusText}</span>
    </div>
  {/if}

  <!-- Help chat -->
  {#if app.modal === 'help'}
    <div class="chat-pop">
      <HelpChat />
    </div>
  {/if}

  <!-- Review modal -->
  {#if app.modal === 'review'}
    <div class="scrim" onclick={(event) => event.target === event.currentTarget && (app.modal = null)} role="presentation">
      <div class="modal-card review-card" role="dialog" aria-modal="true" aria-label="Review your items" tabindex="-1" use:focusDialog>
        <h2 class="modal-title">Everything look right?</h2>
        <p class="modal-sub review-sub">Confirm your items before finishing.</p>
        <div class="review-lines">
          {#each app.cart as item (item.key)}
            <div class="review-line">
              <span class="line-name">{item.qty} × {item.name}</span>
              <span class="line-price tnum">{money(item.price * item.qty)}</span>
            </div>
          {/each}
        </div>
        <div class="modal-total">
          <span class="modal-total-label">Total</span>
          <span class="modal-total-value tnum">{money(total)}</span>
        </div>
        <div class="modal-actions">
          <button class="btn-line modal-btn" onclick={() => (app.modal = null)}>Keep scanning</button>
          <button class="btn-red modal-btn" onclick={confirmCheckout}>Confirm items</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Start over modal -->
  {#if app.modal === 'startover'}
    <div class="scrim" onclick={(event) => event.target === event.currentTarget && (app.modal = null)} role="presentation">
      <div class="modal-card startover-card" role="dialog" aria-modal="true" aria-label="Start a new checkout" tabindex="-1" use:focusDialog>
        <h2 class="modal-title">Start a new checkout?</h2>
        <p class="modal-sub startover-sub">This clears the items in your basket.</p>
        <div class="modal-actions">
          <button class="btn-line modal-btn small" onclick={() => (app.modal = null)}>Keep my items</button>
          <button class="btn-red modal-btn small" onclick={clearBasket}>Start over</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .kiosk {
    position: absolute;
    inset: 0;
    background: var(--cam);
    overflow: hidden;
    animation: fadeIn 0.25s ease both;
  }

  .video {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }
  .camera-feed {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    pointer-events: none;
  }
  .video.live .camera-feed {
    opacity: 0.75;
  }
  .video.live .video-title,
  .video.live .video-sub {
    text-shadow: 0 1px 6px rgba(0, 0, 0, 0.8);
  }
  .det-box {
    position: absolute;
    border: 2px solid var(--green-bg);
    border-radius: 12px;
    background: rgba(220, 229, 213, 0.05);
    animation: popIn 0.3s ease both;
  }
  .det-chip {
    position: absolute;
    height: 28px;
    display: flex;
    align-items: center;
    padding: 0 8px;
    background: var(--green-bg);
    color: var(--ink);
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    line-height: 1;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
    animation: popIn 0.3s ease both;
    white-space: nowrap;
  }

  .video-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 24px;
    text-align: center;
  }
  .start-cam {
    margin-top: 10px;
    height: 48px;
    padding: 0 24px;
    font-size: 15px;
  }
  .corner-buddy {
    position: absolute;
    left: 20px;
    bottom: 62px;
    animation: fadeUp 0.3s ease both;
  }
  .video-title {
    max-width: 480px;
    font-size: 24px;
    line-height: 1.15;
    font-weight: 700;
    color: var(--white);
  }
  .video-sub {
    max-width: 440px;
    font-size: 16px;
    line-height: 1.3;
    color: var(--white);
    opacity: 0.85;
  }
  .scanline {
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--green-bg), transparent);
    animation: scan 1.4s ease-in-out infinite;
  }
  @keyframes scan {
    0% {
      top: 14%;
      opacity: 0;
    }
    15% {
      opacity: 1;
    }
    85% {
      opacity: 1;
    }
    100% {
      top: 85%;
      opacity: 0;
    }
  }

  .top-chip {
    position: absolute;
    bottom: 20px;
    left: 20px;
    z-index: 10;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(42, 42, 41, 0.66);
    border: 1px solid rgba(226, 229, 222, 0.14);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    color: var(--surface);
    animation: fadeUp 0.3s ease both;
  }
  .kiosk-name {
    font-size: 12px;
    line-height: 1;
    font-weight: 700;
    color: var(--white);
  }
  .cam-state {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    line-height: 1;
    opacity: 0.9;
  }
  .cam-state .dot {
    background: var(--cam-border);
  }
  .cam-state .dot-live {
    background: var(--dot-green);
  }
  .cam-state .dot-starting {
    background: var(--amber-bg);
    animation: pulse 1.2s ease-in-out infinite;
  }

  .mini-actions {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 10;
    display: flex;
    gap: 8px;
    animation: fadeUp 0.3s ease both;
  }
  .mini-btn {
    padding: 12px 20px;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    color: var(--ink);
    font-size: 14px;
    font-weight: 700;
    line-height: 1;
    transition: background 0.15s ease;
  }
  .mini-btn:hover {
    background: var(--chip);
  }

  .side {
    position: absolute;
    top: 20px;
    right: 20px;
    bottom: 20px;
    z-index: 10;
    width: 360px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    animation: fadeUp 0.3s ease both;
  }
  .cart {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 18px 20px 20px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  }
  .cart-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
  }
  .cart-title {
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
  }
  .cart-count {
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .cart-items {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    margin-top: 16px;
  }
  .cart-row {
    position: relative;
    height: 72px;
    animation: fadeUp 0.25s ease both;
  }
  .cart-thumb {
    position: absolute;
    left: 0;
    top: 0;
    width: 40px;
    height: 44px;
    background: var(--chip);
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(23, 23, 23, 0.12);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink);
  }
  .cart-name {
    position: absolute;
    left: 52px;
    top: 2px;
    max-width: calc(100% - 150px);
    font-size: 16px;
    line-height: 1;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cart-price {
    position: absolute;
    right: 0;
    top: 1px;
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
  }
  .step-btn {
    position: absolute;
    top: 30px;
    font-size: 20px;
    line-height: 1;
    color: var(--ink);
    padding: 2px 6px;
    border-radius: 6px;
  }
  .step-btn:hover {
    background: var(--chip);
  }
  .step-btn.minus {
    left: 58px;
  }
  .step-btn.plus {
    left: 126px;
  }
  .cart-qty {
    position: absolute;
    left: 100px;
    top: 33px;
    width: 22px;
    text-align: center;
    font-size: 16px;
    line-height: 1;
  }
  .remove-btn {
    position: absolute;
    right: 0;
    top: 38px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .remove-btn:hover {
    color: var(--red);
    text-decoration: underline;
  }
  .cart-empty {
    flex: 1;
    justify-content: center;
  }
  .cart-empty .empty-title {
    font-size: 16px;
  }
  .cart-empty .empty-sub {
    margin-top: 8px;
    font-size: 13px;
  }
  .total-row {
    margin-top: 12px;
    flex-shrink: 0;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .total-label {
    font-size: 16px;
    line-height: 1;
  }
  .total-value {
    font-size: 28px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.5px;
    animation: tick 0.25s ease both;
  }
  @keyframes tick {
    from {
      transform: scale(1.08);
    }
    to {
      transform: scale(1);
    }
  }
  .finish-btn {
    margin-top: 14px;
    flex-shrink: 0;
    width: 100%;
    height: 56px;
    font-size: 18px;
  }
  .finish-btn.waiting {
    font-size: 16px;
    font-weight: 500;
  }

  .help-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    height: 58px;
    padding: 0 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
    transition: background 0.15s ease;
  }
  .help-btn:hover {
    background: var(--chip);
  }
  .help-btn.open {
    background: var(--chip);
    border-color: var(--muted);
  }
  .help-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--chip);
    color: var(--ink);
    flex-shrink: 0;
  }
  .help-btn.open .help-icon {
    background: var(--surface);
  }
  .help-label {
    font-size: 16px;
    font-weight: 700;
    line-height: 1;
  }
  .status-pill {
    position: absolute;
    bottom: 20px;
    left: 0;
    right: 400px;
    margin: 0 auto;
    width: max-content;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 44px;
    max-width: calc(100% - 640px);
    padding: 10px 18px;
    border-radius: 999px;
    background: var(--chip);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    transition: background 0.3s ease;
    animation: fadeUp 0.3s ease both;
  }
  .status-pill.busy {
    background: var(--amber-bg);
  }
  .status-pill.done {
    background: var(--green-bg);
  }
  .status-icon {
    display: flex;
    color: var(--ink);
    flex-shrink: 0;
  }
  .status-pill.busy .status-icon {
    color: var(--amber);
  }
  .status-icon.spin :global(svg) {
    animation: spin 1.1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .status-text {
    font-size: 14px;
    line-height: 1.3;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .chat-pop {
    position: absolute;
    right: 20px;
    bottom: 90px;
    z-index: 40;
    width: 360px;
    height: 460px;
    max-height: calc(100% - 130px);
    animation: popIn 0.2s ease both;
  }

  .scrim {
    position: absolute;
    inset: 0;
    background: rgba(23, 23, 23, 0.48);
    display: grid;
    place-items: center;
    z-index: 50;
    padding: 24px;
    animation: fadeIn 0.18s ease both;
  }
  .modal-card {
    position: relative;
    width: 100%;
    background: var(--surface);
    border-radius: 14px;
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
    animation: popIn 0.2s ease both;
    display: flex;
    flex-direction: column;
    max-height: 100%;
  }
  .review-card {
    max-width: 600px;
    padding: 28px 32px 32px;
  }
  .startover-card {
    max-width: 560px;
    padding: 28px 32px 32px;
  }
  .modal-title {
    font-size: 28px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
  .modal-sub {
    margin-top: 12px;
    font-size: 17px;
    line-height: 1.35;
    color: var(--ink);
  }
  .review-lines {
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    overflow-y: auto;
    min-height: 0;
  }
  .review-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .line-name {
    font-size: 18px;
    line-height: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .line-price {
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
    flex-shrink: 0;
  }
  .modal-total {
    margin-top: 24px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .modal-total-label {
    font-size: 20px;
    line-height: 1;
    font-weight: 700;
  }
  .modal-total-value {
    font-size: 30px;
    line-height: 1;
    font-weight: 700;
  }
  .modal-actions {
    margin-top: 28px;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
  .modal-btn {
    flex: 1;
    min-width: 200px;
    height: 56px;
    font-size: 18px;
  }
  .modal-btn.small {
    font-size: 16px;
  }

  @media (max-width: 1100px) {
    .side {
      top: auto;
      left: 16px;
      right: 16px;
      bottom: 16px;
      width: auto;
      max-height: 52%;
    }
    .help-btn {
      height: 50px;
    }
    .status-pill {
      top: 16px;
      bottom: auto;
      left: auto;
      right: 16px;
      margin: 0;
      max-width: calc(100% - 260px);
    }
    .status-text {
      white-space: normal;
    }
    .mini-actions {
      top: 56px;
      left: 16px;
    }
    .top-chip {
      top: 16px;
      bottom: auto;
      left: 16px;
    }
    .corner-buddy {
      display: none;
    }
    .video-overlay {
      justify-content: flex-start;
      padding: 14vh 24px 24px;
    }
    .chat-pop {
      left: 16px;
      right: 16px;
      bottom: 76px;
      width: auto;
      height: 420px;
      max-height: calc(100% - 190px);
    }
  }
  @media (max-width: 640px) {
    .status-pill {
      max-width: calc(100% - 210px);
      padding: 8px 14px;
    }
    .status-text {
      font-size: 13px;
    }
    .modal-btn {
      min-width: 100%;
    }
  }
</style>
