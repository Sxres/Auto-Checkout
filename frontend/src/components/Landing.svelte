<script>
  import Icon from '../lib/Icon.svelte'
  import { app, go, startCheckout } from '../lib/state.svelte.js'

  let pin = $state('')
  let error = $state(false)

  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'Clear', '0', 'back']

  function press(k) {
    error = false
    if (k === 'Clear') pin = ''
    else if (k === 'back') pin = pin.slice(0, -1)
    else if (pin.length < 6) pin += k
  }

  function unlock() {
    if (pin.length !== 6) return
    if (app.pin && pin !== app.pin) {
      error = true
      pin = ''
      return
    }
    pin = ''
    go('manager', 'overview')
  }

  $effect(() => {
    const onKey = (e) => {
      if (e.key >= '0' && e.key <= '9') press(e.key)
      else if (e.key === 'Backspace') press('back')
      else if (e.key === 'Escape') press('Clear')
      else if (e.key === 'Enter') unlock()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
</script>

<div class="landing">
  <!-- Hero -->
  <section class="hero">
    <h1 class="hero-title">Less scanning.<br />More going.</h1>
    <p class="hero-sub">Start a checkout with the camera view.</p>
    <div class="hero-art" aria-hidden="true">
      <span class="art"><Icon name="basket" size={56} stroke={1.5} /></span>
      <span class="art scan"><Icon name="scan" size={56} stroke={1.5} /></span>
      <span class="art"><Icon name="checkCircle" size={56} stroke={1.5} /></span>
    </div>
    <button class="btn-red start" onclick={startCheckout}>Start checkout</button>
  </section>

  <!-- Manager access -->
  <section class="gate card" class:shake={error}>
    <div class="gate-head">
      <span class="lock-chip"><Icon name="lock" size={20} /></span>
      <h2 class="gate-title">Manager access</h2>
    </div>
    <p class="gate-sub">Enter your 6-digit PIN to open the console.</p>

    <p class="pin-label">Manager PIN</p>
    <div class="pin-boxes">
      {#each Array(6) as _, i}
        <div class="pin-box" class:filled={i < pin.length} class:next={i === pin.length && !error}>
          {#if i < pin.length}<span class="pin-dot"></span>{/if}
        </div>
      {/each}
    </div>
    {#if error}<p class="pin-error">Incorrect PIN. Try again.</p>{/if}

    <div class="keypad">
      {#each keys as k}
        <button
          class="key"
          class:wide-label={k === 'Clear'}
          onclick={() => press(k)}
          aria-label={k === 'back' ? 'Backspace' : k}
        >
          {#if k === 'back'}<Icon name="backspace" size={18} />{:else}{k}{/if}
        </button>
      {/each}
    </div>

    <button class="btn-red unlock" disabled={pin.length !== 6} onclick={unlock}>Unlock console</button>
    <p class="gate-note">For authorized managers only</p>
  </section>
</div>

<style>
  .landing {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: 1.39fr 1fr;
    gap: 32px;
    padding: 64px;
    overflow-y: auto;
    animation: fadeIn 0.3s ease both;
  }

  .hero {
    display: flex;
    flex-direction: column;
    min-height: 620px;
    padding: 48px;
    background: var(--ink);
    border-radius: 14px;
    animation: fadeUp 0.4s ease both;
  }
  .hero-title {
    margin-top: 60px;
    font-size: clamp(34px, 3.4vw, 48px);
    line-height: 1.375;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--surface);
  }
  .hero-sub {
    margin-top: 20px;
    font-size: 14px;
    line-height: 1;
    color: var(--bg);
  }
  .hero-art {
    margin-top: 48px;
    margin-bottom: 48px;
    height: 188px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-around;
    background: var(--dark2);
    border-radius: 10px;
  }
  .art {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--surface);
  }
  .art.scan {
    color: var(--red);
  }
  .start {
    margin-top: auto;
    height: 56px;
    width: 100%;
    font-size: 13px;
  }

  .gate {
    display: flex;
    flex-direction: column;
    min-height: 620px;
    padding: 32px;
    animation: fadeUp 0.4s ease 0.06s both;
  }
  .gate-head {
    display: flex;
    align-items: center;
    gap: 18px;
  }
  .lock-chip {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--chip);
    border-radius: 10px;
    color: var(--ink);
    flex-shrink: 0;
  }
  .gate-title {
    font-size: 20px;
    line-height: 1;
    font-weight: 700;
  }
  .gate-sub {
    margin-top: 15px;
    font-size: 14px;
    line-height: 1;
    color: var(--muted);
  }
  .pin-label {
    margin-top: 35px;
    font-size: 11px;
    line-height: 1;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--muted);
  }
  .pin-boxes {
    margin-top: 20px;
    display: flex;
    gap: 10px;
  }
  .pin-box {
    flex: 1;
    min-width: 0;
    height: 58px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 0.15s ease;
  }
  .pin-box.next {
    border-color: var(--muted);
  }
  .pin-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--ink);
    animation: popIn 0.12s ease both;
  }
  .pin-error {
    margin-top: 6px;
    font-size: 12px;
    line-height: 1;
    font-weight: 600;
    color: var(--red);
  }

  .keypad {
    margin-top: 24px;
    flex: 1 0 auto;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(4, minmax(50px, 1fr));
    gap: 8px;
  }
  .key {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.12s ease, transform 0.04s ease;
  }
  .key:hover {
    background: var(--chip);
  }
  .key:active {
    transform: scale(0.97);
  }
  .key.wide-label {
    font-size: 12px;
  }

  .unlock {
    margin-top: 24px;
    flex-shrink: 0;
    height: 52px;
    width: 100%;
    font-size: 13px;
  }
  .gate-note {
    margin-top: 18px;
    text-align: center;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }

  .shake {
    animation: shake 0.4s ease;
  }
  @keyframes shake {
    0%,
    100% {
      transform: translateX(0);
    }
    20%,
    60% {
      transform: translateX(-6px);
    }
    40%,
    80% {
      transform: translateX(6px);
    }
  }

  @media (max-width: 980px) {
    .landing {
      grid-template-columns: 1fr;
      grid-auto-rows: max-content;
      padding: 32px;
    }
    .hero,
    .gate {
      min-height: 0;
    }
    .hero-title {
      margin-top: 24px;
    }
    .start,
    .unlock {
      margin-top: 32px;
    }
  }
</style>
