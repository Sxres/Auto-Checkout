<script>
  import { onMount } from 'svelte'
  import Icon from '../../lib/Icon.svelte'
  import ProductArt from '../../lib/ProductArt.svelte'
  import {
    app,
    go,
    cartCount,
    cartTotal,
    recognize,
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
  const canRecognize = $derived(cameraState === 'live' && app.phase === 'empty')
  const statusText = $derived.by(() => {
    if (cameraState === 'starting') return 'Connecting to your camera…'
    if (cameraState === 'error') return 'Camera unavailable. Check access and try again.'
    if (cameraState === 'idle') return 'Start the camera to begin your checkout.'
    if (app.phase === 'items') return `${count} item${count === 1 ? '' : 's'} recognized. Ready for your next item.`
    if (app.phase === 'recognizing') return 'Recognizing your items…'
    return 'Ready to scan. Place your first item in view.'
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
  <div class="main">
    <!-- Camera -->
    <div class="camera-card">
      <div class="cam-head">
        <span class="cam-icon"><Icon name="camera" size={16} /></span>
        <h1 class="cam-label">Camera view</h1>
        <span class="camera-status" role="status">
          {cameraState === 'live' ? 'Live' : cameraState === 'starting' ? 'Connecting…' : 'Camera off'}
        </span>
        {#if cameraState === 'idle' || cameraState === 'error'}
          <button class="camera-action" onclick={startCamera}>
            {cameraState === 'idle' ? 'Start camera' : 'Retry camera'}
          </button>
        {/if}
      </div>
      <div
        class="video"
        class:live={cameraState === 'live'}
        class:clickable={canRecognize}
        role="button"
        tabindex={canRecognize ? 0 : -1}
        aria-disabled={!canRecognize}
        aria-label="Recognize items in view"
        onclick={() => canRecognize && recognize()}
        onkeydown={(e) => {
          if (canRecognize && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault()
            recognize()
          }
        }}
      >
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
        {:else}
          <span class="brackets" aria-hidden="true">
            <span class="bracket tl"></span>
            <span class="bracket tr"></span>
            <span class="bracket br"></span>
            <span class="bracket bl"></span>
          </span>
          {#if cameraState !== 'live'}
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
          {:else if app.phase === 'recognizing'}
            <div class="scanline"></div>
            <p class="video-title">Recognizing your items…</p>
            <p class="video-sub">Keep your items still for a moment.</p>
          {:else}
            <p class="video-title">Place your first item.</p>
            <p class="video-sub">We'll recognize it and add it to your basket.</p>
          {/if}
        {/if}
      </div>
    </div>

    <!-- Status strip -->
    <div class="status-strip">
      <span class="status-icon" class:spin={app.phase === 'recognizing'}>
        <Icon name={app.phase === 'items' ? 'checkCircle' : app.phase === 'recognizing' ? 'refresh' : 'scan'} size={18} />
      </span>
      <span class="status-text">{statusText}</span>
    </div>

    <!-- Footer -->
    <div class="footer">
      <button class="btn-line help-btn" onclick={() => (app.modal = 'help')}>Need help?</button>
      <button class="plain-btn startover-btn" onclick={() => (app.modal = 'startover')}>Start over</button>
      <button class="plain-btn staff-btn" onclick={() => go('landing')}>Staff access</button>
    </div>
  </div>

  <!-- Cart -->
  <div class="card cart">
    <div class="cart-head">
      <span class="cart-title">Your items</span>
      <span class="cart-count tnum">{count} item{count === 1 ? '' : 's'}</span>
    </div>

    {#if app.cart.length > 0}
      <div class="cart-items">
        {#each app.cart as item (item.key)}
          <div class="cart-row">
            <span class="cart-thumb"><ProductArt kind={item.art} size={26} /></span>
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
        <span class="icon-chip"><Icon name="basket" size={18} /></span>
        <p class="empty-title">Your basket is empty.</p>
        <p class="empty-sub">Recognized items will appear here.</p>
      </div>
    {/if}

    <div class="total-row">
      <span class="total-label">Total</span>
      <span class="total-value tnum">{money(total)}</span>
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

  <!-- Help modal -->
  {#if app.modal === 'help'}
    <div class="scrim" onclick={(event) => event.target === event.currentTarget && (app.modal = null)} role="presentation">
      <div class="modal-card help-card" role="dialog" aria-modal="true" aria-label="Need help" tabindex="-1" use:focusDialog>
        <h2 class="modal-title">Need a hand?</h2>
        <p class="modal-sub help-body">A team member can help check an item or correct your basket.</p>
        <div class="modal-actions">
          <button class="btn-red modal-btn small" onclick={() => (app.modal = null)}>Back to checkout</button>
          <button class="btn-line modal-btn small" onclick={() => go('landing')}>Staff access</button>
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
    display: grid;
    grid-template-columns: minmax(0, 1fr) 464px;
    grid-template-rows: minmax(0, 1fr);
    column-gap: 32px;
    padding: 32px 64px;
    animation: fadeIn 0.25s ease both;
  }

  .main {
    grid-column: 1;
    grid-row: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .camera-card {
    flex: 1;
    min-height: 320px;
    display: flex;
    flex-direction: column;
    padding: 24px;
    background: var(--dark);
    border-radius: 14px;
  }
  .cam-head {
    display: flex;
    align-items: center;
    gap: 9px;
    flex-wrap: wrap;
    flex-shrink: 0;
  }
  .cam-icon {
    display: flex;
    color: var(--white);
  }
  .cam-label {
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
    color: var(--white);
  }
  .camera-status {
    margin-left: auto;
    font-size: 12px;
    color: var(--surface);
  }
  .camera-action {
    padding: 6px 10px;
    border: 1px solid var(--cam-border);
    border-radius: 6px;
    color: var(--white);
    font-size: 12px;
    font-weight: 600;
  }
  .camera-action:hover {
    background: var(--dark2);
  }
  .video {
    position: relative;
    flex: 1;
    margin-top: 24px;
    background: var(--cam);
    border: 1px solid var(--cam-border);
    border-radius: 4px;
    overflow: hidden;
  }
  .video.clickable {
    cursor: pointer;
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
  .video.live .bracket {
    border-color: var(--surface);
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

  .brackets {
    position: absolute;
    left: 50%;
    top: 40%;
    width: 44px;
    height: 44px;
    transform: translate(-50%, -50%);
  }
  .bracket {
    position: absolute;
    width: 11px;
    height: 11px;
    border-color: var(--cam-border);
    border-style: solid;
    border-width: 0;
  }
  .bracket.tl {
    left: 0;
    top: 0;
    border-left-width: 2px;
    border-top-width: 2px;
  }
  .bracket.tr {
    right: 0;
    top: 0;
    border-right-width: 2px;
    border-top-width: 2px;
  }
  .bracket.br {
    right: 0;
    bottom: 0;
    border-right-width: 2px;
    border-bottom-width: 2px;
  }
  .bracket.bl {
    left: 0;
    bottom: 0;
    border-left-width: 2px;
    border-bottom-width: 2px;
  }
  .video-title {
    position: absolute;
    left: 16px;
    right: 16px;
    top: 50%;
    text-align: center;
    font-size: 24px;
    line-height: 1;
    font-weight: 700;
    color: var(--white);
  }
  .video-sub {
    position: absolute;
    left: 16px;
    right: 16px;
    top: 61%;
    text-align: center;
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

  .status-strip {
    margin-top: 16px;
    height: 52px;
    flex-shrink: 0;
    background: var(--green-bg);
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(23, 23, 23, 0.1);
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 0 17px;
  }
  .status-icon {
    display: flex;
    color: var(--ink);
    flex-shrink: 0;
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
    font-size: 17px;
    line-height: 1.2;
    color: var(--ink);
  }

  .footer {
    margin-top: 24px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
  }
  .help-btn {
    width: 208px;
    height: 56px;
    font-size: 18px;
  }
  .plain-btn {
    line-height: 1;
    font-weight: 700;
    color: var(--ink);
  }
  .plain-btn:hover {
    text-decoration: underline;
    text-underline-offset: 4px;
  }
  .startover-btn {
    font-size: 18px;
  }
  .staff-btn {
    margin-left: auto;
    font-size: 16px;
    font-weight: 500;
    color: var(--muted);
  }

  .cart {
    grid-column: 2;
    grid-row: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 22px 25px 25px;
  }
  .cart-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
  }
  .cart-title {
    font-size: 22px;
    line-height: 1;
    font-weight: 700;
  }
  .cart-count {
    font-size: 14px;
    line-height: 1;
    color: var(--muted);
  }
  .cart-items {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    margin-top: 24px;
  }
  .cart-row {
    position: relative;
    height: 80px;
    animation: fadeUp 0.25s ease both;
  }
  .cart-thumb {
    position: absolute;
    left: 0;
    top: 0;
    width: 44px;
    height: 48px;
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
    left: 56px;
    top: 2px;
    max-width: calc(100% - 160px);
    font-size: 18px;
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
    font-size: 20px;
    line-height: 1;
    font-weight: 700;
  }
  .step-btn {
    position: absolute;
    top: 33px;
    font-size: 22px;
    line-height: 1;
    color: var(--ink);
    padding: 2px 6px;
    border-radius: 6px;
  }
  .step-btn:hover {
    background: var(--chip);
  }
  .step-btn.minus {
    left: 65px;
  }
  .step-btn.plus {
    left: 137px;
  }
  .cart-qty {
    position: absolute;
    left: 110px;
    top: 36px;
    width: 24px;
    text-align: center;
    font-size: 18px;
    line-height: 1;
  }
  .remove-btn {
    position: absolute;
    right: 0;
    top: 43px;
    font-size: 13px;
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
    font-size: 20px;
  }
  .cart-empty .empty-sub {
    margin-top: 14px;
    font-size: 15px;
  }
  .total-row {
    margin-top: 16px;
    flex-shrink: 0;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .total-label {
    font-size: 18px;
    line-height: 1;
  }
  .total-value {
    font-size: 32px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.5px;
  }
  .finish-btn {
    margin-top: 20px;
    flex-shrink: 0;
    width: 100%;
    height: 64px;
    font-size: 20px;
  }
  .finish-btn.waiting {
    font-size: 18px;
    font-weight: 500;
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
  .help-card,
  .startover-card {
    max-width: 560px;
    padding: 35px 32px 32px;
  }
  .modal-title {
    font-size: 28px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
  .modal-sub {
    font-size: 17px;
    line-height: 1.35;
    color: var(--ink);
  }
  .review-sub {
    margin-top: 35px;
  }
  .help-body {
    margin-top: 32px;
  }
  .startover-sub {
    margin-top: 32px;
  }
  .review-lines {
    margin-top: 32px;
    display: flex;
    flex-direction: column;
    gap: 38px;
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
    margin-top: 32px;
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
    margin-top: 30px;
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

  @media (max-width: 1200px) {
    .kiosk {
      grid-template-columns: minmax(0, 1fr) 400px;
      padding: 32px 40px;
    }
  }
  @media (max-width: 1000px) {
    .kiosk {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto;
      overflow-y: auto;
    }
    .main {
      min-height: max(640px, calc(100svh - 64px));
    }
    .cart {
      grid-column: 1;
      grid-row: 2;
      margin-top: 24px;
      min-height: 480px;
    }
  }
  @media (max-width: 640px) {
    .kiosk {
      padding: 28px 20px 24px;
    }
    .main {
      min-height: max(640px, calc(100svh - 52px));
    }
    .help-btn {
      width: 100%;
    }
    .staff-btn {
      margin-left: 0;
    }
    .modal-btn {
      min-width: 100%;
    }
  }
</style>
