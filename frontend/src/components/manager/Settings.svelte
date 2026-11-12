<script>
  import Icon from '../../lib/Icon.svelte'
  import Toggle from '../../lib/Toggle.svelte'
  import Modal from '../../lib/Modal.svelte'
  import PageHead from './PageHead.svelte'
  import { app, persist, toast, startCheckout } from '../../lib/state.svelte.js'

  let pinOpen = $state(false)
  let newPin = $state('')
  let confirmPin = $state('')

  const pinValid = $derived(/^\d{6}$/.test(newPin) && newPin === confirmPin)

  const cameras = ['Camera 01: Integrated webcam', 'Camera 02: USB camera']
  const qualities = ['1080p · 30 fps', '1080p · 60 fps', '720p · 30 fps']
  const retentions = ['7 days', '14 days', '30 days', '90 days']
  const lockOptions = ['1 minute', '5 minutes', '15 minutes', '30 minutes']

  const connRows = $derived([
    {
      label: 'Camera',
      value: app.kioskStatus.cameraConnected ? 'Connected' : 'Not connected',
      ok: app.kioskStatus.cameraConnected,
    },
    { label: 'Kiosk', value: app.kioskStatus.online ? 'Ready' : 'Offline', ok: app.kioskStatus.online },
    { label: 'Last check', value: app.kioskStatus.lastCheck ?? '—', ok: app.kioskStatus.lastCheck != null },
  ])

  function save() {
    persist()
    toast('Settings saved.')
  }

  function savePin() {
    if (!pinValid) return
    app.pin = newPin
    persist()
    pinOpen = false
    newPin = ''
    confirmPin = ''
    toast('Manager PIN updated.')
  }

  function onlyDigits(v) {
    return v.replace(/\D/g, '').slice(0, 6)
  }
</script>

<div class="page">
  <PageHead title="Settings" subtitle="Manage the kiosk, camera, and manager access.">
    <button class="btn-red head-btn" onclick={save}>Save changes</button>
  </PageHead>

  <div class="grid">
    <div class="col-left">
      <!-- Camera & kiosk -->
      <div class="card camera-card">
        <h2 class="card-title">Camera &amp; kiosk</h2>
        <div class="cam-grid">
          <div class="field-group">
            <label class="field-label" for="kiosk-name">Kiosk name</label>
            <input id="kiosk-name" class="field bold-input" bind:value={app.kioskName} />
          </div>
          <div class="field-group">
            <label class="field-label" for="camera-source">Camera source</label>
            <div class="select-wrap">
              <select id="camera-source" class="field select" bind:value={app.settings.cameraSource}>
                {#each cameras as c}<option>{c}</option>{/each}
              </select>
              <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
            </div>
          </div>
          <div class="field-group">
            <label class="field-label" for="capture-quality">Capture quality</label>
            <div class="select-wrap">
              <select id="capture-quality" class="field select" bind:value={app.settings.quality}>
                {#each qualities as q}<option>{q}</option>{/each}
              </select>
              <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
            </div>
          </div>
          <div class="toggle-group">
            <div class="pref-text">
              <span class="toggle-title">Start camera automatically</span>
              <span class="toggle-desc">Ready when a checkout begins.</span>
            </div>
            <Toggle value={app.settings.autoStart} onchange={(v) => (app.settings.autoStart = v)} label="Start camera automatically" />
          </div>
        </div>
      </div>

      <!-- Recognition preferences -->
      <div class="card prefs-card">
        <h2 class="card-title">Recognition preferences</h2>
        <div class="pref-row">
          <div class="pref-text">
            <span class="toggle-title">Ask for help on uncertain items</span>
            <span class="toggle-desc">Send low-confidence scans to the review queue.</span>
          </div>
          <Toggle value={app.settings.askHelp} onchange={(v) => (app.settings.askHelp = v)} label="Ask for help on uncertain items" />
        </div>
        <div class="divider prefs-divider"></div>
        <div class="pref-row second">
          <span class="toggle-title">Use corrected scans in future training</span>
          <Toggle value={app.settings.useCorrections} onchange={(v) => (app.settings.useCorrections = v)} label="Use corrected scans in future training" />
        </div>
      </div>

      <!-- Manager access -->
      <div class="card access-card">
        <h2 class="card-title">Manager access</h2>
        <div class="access-row pin-row">
          <div class="pin-info">
            <span class="toggle-title">Manager PIN</span>
            <span class="pin-dots">{app.pin ? '••••••' : 'Not set'}</span>
          </div>
          <button class="btn-line change-btn" onclick={() => (pinOpen = true)}>Change</button>
        </div>
        <div class="divider access-divider"></div>
        <div class="access-row lock-row">
          <span class="toggle-title">Lock console after inactivity</span>
          <div class="select-wrap lock-select">
            <select class="field select small-select" bind:value={app.settings.lockAfter} aria-label="Lock console after inactivity">
              {#each lockOptions as l}<option>{l}</option>{/each}
            </select>
            <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
          </div>
        </div>
      </div>
    </div>

    <div class="col-right">
      <!-- Connection check -->
      <div class="card connection-card">
        <span class="small-title">Connection check</span>
        <div class="conn-rows">
          {#each connRows as row}
            <div class="conn-row">
              <span class="conn-icon" class:ok={row.ok}>
                <Icon name={row.ok ? 'checkCircle' : 'info'} size={16} />
              </span>
              <span class="conn-label">{row.label}</span>
              <span class="conn-value">{row.value}</span>
            </div>
          {/each}
        </div>
        <button class="btn-line conn-btn" onclick={startCheckout}>Open camera view</button>
      </div>

      <!-- Saved scans -->
      <div class="card scans-card">
        <span class="small-title">Saved scans</span>
        <label class="field-label scans-label" for="retention">Keep reviewed images for</label>
        <div class="select-wrap scans-select">
          <select id="retention" class="field select" bind:value={app.settings.retention}>
            {#each retentions as r}<option>{r}</option>{/each}
          </select>
          <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
        </div>
      </div>

      <!-- Manager-only note -->
      <div class="note-card">
        <div class="note-head">
          <span class="note-icon"><Icon name="lock" size={20} /></span>
          <span class="note-title">Manager-only controls</span>
        </div>
        <p class="note-line">A PIN is required to open this workspace.</p>
        <p class="note-line">Lock the console when stepping away.</p>
      </div>
    </div>
  </div>
</div>

{#if pinOpen}
  <Modal title="Change manager PIN" onclose={() => (pinOpen = false)}>
    {#snippet footer()}
      <button class="btn-line modal-btn" onclick={() => (pinOpen = false)}>Cancel</button>
      <button class="btn-red modal-btn" disabled={!pinValid} onclick={savePin}>Save PIN</button>
    {/snippet}
    <p class="pin-note">
      {app.pin ? 'Enter a new 6-digit PIN for this console.' : 'No PIN is set yet — any 6 digits unlock the console. Set one to lock it down.'}
    </p>
    <label class="form-label" for="new-pin">New PIN</label>
    <input
      id="new-pin"
      class="field form-input pin-input"
      type="password"
      inputmode="numeric"
      autocomplete="new-password"
      placeholder="••••••"
      value={newPin}
      oninput={(e) => (newPin = onlyDigits(e.currentTarget.value))}
    />
    <label class="form-label" for="confirm-pin">Confirm PIN</label>
    <input
      id="confirm-pin"
      class="field form-input pin-input"
      type="password"
      inputmode="numeric"
      autocomplete="new-password"
      placeholder="••••••"
      value={confirmPin}
      oninput={(e) => (confirmPin = onlyDigits(e.currentTarget.value))}
    />
    {#if confirmPin && !pinValid}
      <p class="pin-error">PINs must match and be 6 digits.</p>
    {/if}
  </Modal>
{/if}

<style>
  .page {
    animation: fadeIn 0.25s ease both;
  }
  .head-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 12px;
  }

  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 376px;
    gap: 24px;
    align-items: start;
  }
  .col-left,
  .col-right {
    display: flex;
    flex-direction: column;
    gap: 24px;
    min-width: 0;
  }

  .card-title {
    font-size: 17px;
    line-height: 1;
    font-weight: 700;
  }
  .small-title {
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .field-label {
    display: block;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
    margin-bottom: 7px;
  }
  .bold-input {
    width: 100%;
    height: 44px;
    font-size: 13px;
    font-weight: 700;
  }
  .select-wrap {
    position: relative;
    height: 44px;
  }
  .select {
    width: 100%;
    height: 100%;
    appearance: none;
    padding-right: 36px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 700;
  }
  .small-select {
    font-size: 12px;
  }
  .select-chev {
    position: absolute;
    right: 12px;
    top: 15px;
    display: flex;
    color: var(--muted);
    pointer-events: none;
  }
  .toggle-title {
    font-size: 13px;
    line-height: 1.3;
    font-weight: 700;
  }
  .toggle-desc {
    font-size: 11px;
    line-height: 1.3;
    color: var(--muted);
  }
  .pref-text {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .camera-card {
    min-height: 260px;
    padding: 21px 24px 24px;
  }
  .cam-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px 24px;
    margin-top: 33px;
  }
  .toggle-group {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .connection-card {
    height: 246px;
    display: flex;
    flex-direction: column;
    padding: 21px 24px 24px;
  }
  .conn-rows {
    display: flex;
    flex-direction: column;
    gap: 28px;
    margin-top: 36px;
  }
  .conn-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .conn-icon {
    display: flex;
    color: var(--muted);
  }
  .conn-icon.ok {
    color: var(--green);
  }
  .conn-label {
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .conn-value {
    margin-left: auto;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .conn-btn {
    margin-top: auto;
    width: 100%;
    height: 34px;
    font-size: 13px;
  }

  .prefs-card {
    min-height: 182px;
    padding: 21px 24px 24px;
  }
  .pref-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-top: 22px;
  }
  .pref-row.second {
    margin-top: 21px;
  }
  .prefs-divider {
    margin-top: 16px;
  }

  .scans-card {
    min-height: 178px;
    padding: 21px 24px 24px;
  }
  .scans-label {
    margin-top: 38px;
  }

  .access-card {
    min-height: 198px;
    padding: 21px 24px 24px;
  }
  .access-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .pin-row {
    margin-top: 16px;
  }
  .pin-info {
    display: flex;
    flex-direction: column;
    gap: 11px;
  }
  .pin-dots {
    font-size: 12px;
    line-height: 1;
    letter-spacing: 2px;
    color: var(--muted);
  }
  .change-btn {
    width: 162px;
    height: 38px;
    font-size: 13px;
    flex-shrink: 0;
  }
  .access-divider {
    margin-top: 18px;
  }
  .lock-row {
    margin-top: 16px;
    flex-wrap: wrap;
  }
  .lock-select {
    width: 162px;
    flex-shrink: 0;
  }

  .note-card {
    min-height: 136px;
    background: var(--chip);
    border-radius: 14px;
    padding: 22px 24px;
  }
  .note-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }
  .note-icon {
    display: flex;
    color: var(--ink);
  }
  .note-title {
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .note-line {
    font-size: 11px;
    line-height: 1.6;
    color: var(--muted);
  }

  .pin-note {
    font-size: 13px;
    line-height: 1.5;
    color: var(--muted);
    margin-bottom: 18px;
  }
  .form-label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .form-input {
    width: 100%;
    margin-bottom: 18px;
  }
  .pin-input {
    letter-spacing: 6px;
    font-weight: 700;
  }
  .pin-error {
    font-size: 12px;
    color: var(--red);
    margin-top: -6px;
  }
  .modal-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 13px;
  }

  @media (max-width: 1100px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 640px) {
    .cam-grid {
      grid-template-columns: 1fr;
    }
    .change-btn,
    .lock-select {
      width: 130px;
    }
  }
</style>
