<script>
  import Icon from '../../lib/Icon.svelte'
  import PageHead from './PageHead.svelte'
  import { app, go, startTraining, publishVersion } from '../../lib/state.svelte.js'

  const live = $derived(app.versions.find((v) => v.status === 'Live'))
  const training = $derived(app.training)
  const pct = $derived(training ? Math.round(training.progress * 100) : 0)
  const done = $derived(training?.progress >= 1)
  const shown = $derived(app.versions.slice(0, 3))
  const canTrain = $derived(app.products.length > 0 || app.dataset.scans > 0)

  const steps = [
    { title: 'Choose your images', desc: 'Reviewed scans + product photos' },
    { title: 'Train a new version', desc: 'Your current version stays live during training.' },
    { title: 'Review and publish', desc: 'Compare the result before switching versions.' },
  ]

  function stepState(i) {
    if (i === 0) return true
    if (i === 1) return !!training
    return done
  }
</script>

<div class="page">
  <PageHead title="Retraining" subtitle="Improve recognition with reviewed scans and product photos.">
    <button class="btn-red head-btn" onclick={() => go('manager', 'review')}>Review queue</button>
  </PageHead>

  <div class="grid">
    <div class="col-left">
      <!-- Prepare a new version -->
      <div class="card prep-card">
        <h2 class="prep-title">Ready for a refresh</h2>
        <p class="prep-sub">Prepare a new version in three simple steps.</p>

        <div class="steps">
          {#each steps as s, i}
            <div class="step">
              <span class="step-circle {stepState(i) ? 'on' : ''}">{i + 1}</span>
              <div class="step-text">
                <span class="step-title">{s.title}</span>
                <span class="step-desc">{s.desc}</span>
              </div>
            </div>
          {/each}
        </div>

        <div class="dataset">
          <span class="dataset-label">
            {#if !training}{canTrain ? 'DATASET READY' : 'DATASET EMPTY'}{:else if !done}TRAINING… {pct}%{:else}VERSION READY{/if}
          </span>
          <span class="dataset-value">
            {#if !training}
              {app.dataset.scans} reviewed scans · {app.products.length} products
            {:else if !done}
              Building a new version…
            {:else}
              {training.v} · {training.images} images · {training.rate} recognition
            {/if}
          </span>
          {#if done}
            <div class="train-progress done"></div>
          {:else if training}
            <div class="train-progress" style="transform: scaleX({training.progress})"></div>
          {/if}
          <button
            class="btn-red train-btn"
            disabled={(!!training && !done) || (!training && !canTrain)}
            onclick={done ? publishVersion : startTraining}
          >
            {#if !training}{canTrain ? 'Start training' : 'Dataset empty'}{:else if !done}Training… {pct}%{:else}Publish {training.v}{/if}
          </button>
        </div>
      </div>

      <!-- Training history -->
      <div class="card history-card">
        <div class="history-head">
          <h2 class="history-title">Training history</h2>
          <span class="history-count tnum">{app.versions.length} versions</span>
        </div>

        {#if app.versions.length > 0}
          <div class="table">
            <div class="trow thead">
              {#each ['Version', 'Created', 'Images', 'Recognition', 'Status'] as h}
                <span class="th">{h}</span>
              {/each}
            </div>
            {#each shown as v}
              <div class="trow">
                <span class="hist-cell strong tnum">{v.v}</span>
                <span class="hist-cell">{v.created}</span>
                <span class="hist-cell tnum">{v.images}</span>
                <span class="hist-cell tnum">{v.rate}</span>
                <span class="pill hist-pill {v.status === 'Live' ? 'pill-green' : 'pill-gray'}">
                  {#if v.status === 'Live'}<span class="dot"></span>{/if}{v.status}
                </span>
              </div>
            {/each}
          </div>
          {#if app.versions.length > 3}
            <span class="hist-more tnum">Showing 3 of {app.versions.length} versions</span>
          {/if}
        {:else}
          <div class="empty-state history-empty">
            <span class="icon-chip"><Icon name="refresh" size={18} /></span>
            <p class="empty-title">No training runs yet.</p>
            <p class="empty-sub">Published versions will appear here.</p>
          </div>
        {/if}
      </div>
    </div>

    <div class="col-right">
      <!-- Current live version -->
      <div class="card live-card">
        <span class="live-title">Current live version</span>
        <span class="pill live-pill {live ? 'pill-green' : 'pill-gray'}">
          {#if live}<span class="dot"></span>{/if}{live ? 'Live' : 'None'}
        </span>
        <span class="live-v tnum">{live?.v ?? '—'}</span>
        <span class="live-row-label" style="top: 130px">Recognition rate</span>
        <span class="live-row-value tnum" style="top: 129px">{live?.rate ?? '—'}</span>
        <span class="live-row-label" style="top: 164px">Last trained</span>
        <span class="live-row-value" style="top: 163px">{live?.created ?? '—'}</span>
        <div class="divider live-divider"></div>
        <span class="live-note">{live ? 'Your kiosk is using this version.' : 'Publish a version to go live.'}</span>
      </div>

      <!-- Coverage tip -->
      <div class="card tip-card">
        <h2 class="tip-title">More images, better coverage</h2>
        <span class="tip-icon"><Icon name="image" size={20} /></span>
        <span class="tip-text">Add different angles and lighting.</span>
        <button
          class="btn-line tip-btn"
          onclick={() => {
            app.catalogImagesRequest++
            go('manager', 'catalog')
          }}
        >
          Add training images
        </button>
      </div>
    </div>
  </div>
</div>

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
    min-width: 0;
  }

  .prep-card {
    min-height: 414px;
    display: flex;
    flex-direction: column;
    padding: 21px 24px 24px;
  }
  .prep-title {
    font-size: 17px;
    line-height: 1;
    font-weight: 700;
  }
  .prep-sub {
    margin-top: 10px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .steps {
    margin-top: 11px;
    display: flex;
    flex-direction: column;
    gap: 37px;
  }
  .step {
    display: flex;
    align-items: center;
    gap: 19px;
  }
  .step-circle {
    width: 38px;
    height: 38px;
    flex-shrink: 0;
    border-radius: 50%;
    background: var(--chip);
    color: var(--ink);
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.25s ease, color 0.25s ease;
  }
  .step-circle.on {
    background: var(--green-bg);
    color: var(--green);
  }
  .step-text {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .step-title {
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .step-desc {
    font-size: 11px;
    line-height: 1.3;
    color: var(--muted);
  }
  .dataset {
    position: relative;
    margin-top: auto;
    height: 82px;
    flex-shrink: 0;
    background: var(--bg);
    border-radius: 10px;
  }
  .dataset-label {
    position: absolute;
    left: 21px;
    top: 20px;
    font-size: 11px;
    line-height: 1;
    letter-spacing: 0.8px;
    font-weight: 600;
    color: var(--muted);
  }
  .dataset-value {
    position: absolute;
    left: 20px;
    top: 43px;
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
    max-width: calc(100% - 240px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .train-progress {
    position: absolute;
    left: 20px;
    top: 64px;
    width: 260px;
    height: 3px;
    max-width: min(260px, calc(100% - 240px));
    border-radius: 2px;
    background: var(--red);
    transform: scaleX(0);
    transform-origin: left center;
    transition: transform 0.15s linear;
  }
  .train-progress.done {
    transform: scaleX(1);
    background: var(--green);
  }
  .train-btn {
    position: absolute;
    right: 20px;
    top: 20px;
    width: 188px;
    height: 42px;
    font-size: 13px;
  }

  .live-card {
    position: relative;
    height: 238px;
  }
  .live-title {
    position: absolute;
    left: 25px;
    top: 21px;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .live-pill {
    position: absolute;
    right: 24px;
    top: 24px;
    height: 26px;
    padding: 0 16px;
    font-size: 11px;
  }
  .live-v {
    position: absolute;
    left: 24px;
    top: 70px;
    font-size: 24px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
  .live-row-label {
    position: absolute;
    left: 24px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .live-row-value {
    position: absolute;
    right: 24px;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .live-divider {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 195px;
  }
  .live-note {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 211px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }

  .tip-card {
    position: relative;
    height: 152px;
    margin-top: 24px;
  }
  .tip-title {
    position: absolute;
    left: 25px;
    top: 21px;
    font-size: 17px;
    line-height: 1;
    font-weight: 700;
  }
  .tip-icon {
    position: absolute;
    left: 26px;
    top: 62px;
    display: flex;
    color: var(--green);
  }
  .tip-text {
    position: absolute;
    left: 62px;
    right: 24px;
    top: 65px;
    font-size: 12px;
    line-height: 1;
    color: var(--ink);
  }
  .tip-btn {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 94px;
    height: 36px;
    font-size: 13px;
  }

  .history-card {
    min-height: 250px;
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    padding: 21px 24px 14px;
  }
  .history-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .history-title {
    font-size: 17px;
    line-height: 1;
    font-weight: 700;
  }
  .history-count {
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .table {
    margin-top: 26px;
  }
  .trow {
    display: grid;
    grid-template-columns: 1fr 1.05fr 1.05fr 0.95fr 110px;
    align-items: center;
    gap: 12px;
    height: 44px;
  }
  .trow + .trow {
    border-top: 1px solid var(--border);
  }
  .thead {
    height: 30px;
    border-bottom: 1px solid var(--border);
  }
  .th {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .hist-cell {
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .hist-cell.strong {
    font-weight: 700;
    color: var(--ink);
  }
  .hist-pill {
    width: 100px;
    height: 26px;
    font-size: 11px;
    font-weight: 700;
  }
  .hist-more {
    margin-top: auto;
    padding-top: 12px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .history-empty {
    flex: 1;
    padding: 28px 24px;
  }

  @media (max-width: 1100px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 640px) {
    .trow {
      grid-template-columns: 1fr 1fr 100px;
    }
    .trow > :nth-child(3),
    .trow > :nth-child(4) {
      display: none;
    }
    .dataset-value {
      max-width: calc(100% - 40px);
    }
    .train-btn {
      position: static;
      margin: 0;
    }
    .dataset {
      height: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .dataset-label,
    .dataset-value {
      position: static;
    }
    .train-progress {
      position: static;
      max-width: 100%;
    }
    .train-btn {
      width: 100%;
    }
  }
</style>
