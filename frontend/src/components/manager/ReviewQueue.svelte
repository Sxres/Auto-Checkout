<script>
  import Icon from '../../lib/Icon.svelte'
  import ProductArt from '../../lib/ProductArt.svelte'
  import PageHead from './PageHead.svelte'
  import { app, go, toast } from '../../lib/state.svelte.js'

  let page = $state(0)
  let newest = $state(true)
  let selectedId = $state(app.review[0]?.id ?? null)
  let choice = $state('')

  const sorted = $derived(newest ? app.review : [...app.review].reverse())
  const pages = $derived(Math.max(1, Math.ceil(sorted.length / 5)))
  const visible = $derived(sorted.slice(page * 5, page * 5 + 5))
  const selected = $derived(app.review.find((r) => r.id === selectedId) ?? app.review[0] ?? null)

  $effect(() => {
    if (page >= pages) page = pages - 1
  })
  $effect(() => {
    choice = selected?.label ?? ''
  })

  function save() {
    if (!selected) return
    const name = choice
    app.review = app.review.filter((r) => r.id !== selected.id)
    app.correctedToday += 1
    selectedId = app.review[0]?.id ?? null
    toast(`Saved “${name}” correction for the next training run.`)
  }
</script>

<div class="page">
  <PageHead title="Review queue" subtitle="Give uncertain items a quick human check.">
    <button class="btn-red head-btn" onclick={() => go('manager', 'retraining')}>Retraining</button>
  </PageHead>

  <div class="toolbar">
    <div class="pills">
      <span class="pill pill-amber wait-pill">
        <Icon name="alert" size={13} />
        {app.review.length} waiting for review
      </span>
      <span class="pill pill-green corrected-pill">
        <Icon name="check" size={13} />
        {app.correctedToday} corrected today
      </span>
    </div>
    <button class="sort-btn" onclick={() => (newest = !newest)}>
      {newest ? 'Newest first' : 'Oldest first'}
      <Icon name="chevronDown" size={13} />
    </button>
  </div>

  <div class="grid">
    <!-- Items list -->
    <div class="card list-card">
      <span class="card-title">Items to review</span>
      <span class="list-sub">Select a scan to check its suggested product.</span>

      <div class="rows">
        {#each visible as item}
          <button
            class="row"
            class:selected={selected && item.id === selected.id}
            onclick={() => (selectedId = item.id)}
          >
            <span class="thumb"><ProductArt kind={item.art} size={28} /></span>
            <span class="row-name">{item.label}</span>
            <span class="row-suggested">Suggested · {item.suggested}</span>
            <span class="pill pill-amber match-pill tnum">{item.match.toFixed(1)}% match</span>
          </button>
        {/each}

        {#if sorted.length === 0}
          <div class="empty-state list-empty">
            <span class="icon-chip"><Icon name="inbox" size={18} /></span>
            <p class="empty-title">All caught up — no scans waiting for review.</p>
            <p class="empty-sub">Low-confidence recognitions will land here for a human check.</p>
          </div>
        {/if}
      </div>

      <div class="list-footer">
        <span class="footer-count tnum">Showing {visible.length} of {sorted.length} items</span>
        {#if sorted.length > 5}
          <button class="next-btn" onclick={() => (page = (page + 1) % pages)}>Next items</button>
        {/if}
      </div>
    </div>

    <!-- Selected scan -->
    <div class="card detail-card">
      <span class="card-title">Selected scan</span>
      {#if selected}
        <span class="detail-time">{selected.time} · {app.kioskName}</span>

        <div class="image-area">
          <div class="capture-card">
            <span class="capture-art"><ProductArt kind={selected.art} width={49} height={65} /></span>
          </div>
          <span class="capture-label">Capture {selected.capture}</span>
        </div>

        <span class="field-label suggested-label">Suggested product</span>
        <span class="suggested-name">{selected.suggested}</span>
        <span class="pill pill-amber detail-match tnum">{selected.match.toFixed(1)}% match</span>

        <span class="field-label correct-label">Correct product</span>
        <div class="select-wrap">
          <select class="field select" bind:value={choice} aria-label="Correct product">
            {#each app.products as p}
              <option value={p.name}>{p.name}</option>
            {/each}
          </select>
          <span class="select-chev"><Icon name="chevronDown" size={16} /></span>
        </div>

        <button class="btn-red save-btn" onclick={save}>Save correction</button>

        <span class="info-icon"><Icon name="info" size={15} /></span>
        <span class="info-text">Saved corrections can be used in the next retraining run.</span>
      {:else}
        <div class="empty-state detail-empty">
          <span class="icon-chip"><Icon name="scan" size={18} /></span>
          <p class="empty-title">Select a scan from the list to review it.</p>
        </div>
      {/if}
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

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 23px;
  }
  .pills {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .wait-pill,
  .corrected-pill {
    height: 26px;
    padding: 0 13px;
    font-size: 12px;
    gap: 6px;
  }
  .sort-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .sort-btn:hover {
    color: var(--ink);
  }

  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 472px;
    gap: 24px;
    align-items: start;
  }

  .card-title {
    position: absolute;
    left: 25px;
    top: 19px;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }

  .list-card {
    position: relative;
    min-height: 640px;
    display: flex;
    flex-direction: column;
    padding: 19px 16px 24px;
  }
  .list-card .card-title {
    position: static;
    margin-left: 9px;
  }
  .list-sub {
    margin: 11px 0 0 9px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .rows {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 24px;
  }
  .row {
    position: relative;
    width: 100%;
    height: 86px;
    flex-shrink: 0;
    border-radius: 10px;
    background: var(--surface);
    text-align: left;
    transition: background 0.15s ease;
  }
  .row:hover:not(.selected) {
    background: var(--bg);
  }
  .row.selected {
    background: var(--chip);
  }
  .thumb {
    position: absolute;
    left: 16px;
    top: 17px;
    width: 52px;
    height: 52px;
    border-radius: 8px;
    background: var(--chip);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .row.selected .thumb {
    background: var(--surface);
  }
  .row-name {
    position: absolute;
    left: 84px;
    top: 20px;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
    color: var(--ink);
    max-width: calc(100% - 230px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row-suggested {
    position: absolute;
    left: 84px;
    top: 45px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
    max-width: calc(100% - 230px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .match-pill {
    position: absolute;
    right: 18px;
    top: 29px;
    width: 120px;
    height: 26px;
    font-size: 11px;
  }
  .list-empty {
    flex: 1;
  }
  .list-footer {
    margin-top: auto;
    padding: 16px 8px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .footer-count {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .next-btn {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .next-btn:hover {
    color: var(--ink);
    text-decoration: underline;
  }

  .detail-card {
    position: relative;
    height: 640px;
  }
  .detail-time {
    position: absolute;
    left: 24px;
    top: 49px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .image-area {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 82px;
    height: 222px;
    background: var(--bg);
    border-radius: 8px;
  }
  .capture-card {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    top: 32px;
    width: 148px;
    height: 158px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .capture-art {
    position: absolute;
    left: 49px;
    top: 42px;
    color: var(--ink);
  }
  .capture-label {
    position: absolute;
    left: 0;
    right: 0;
    top: 195px;
    text-align: center;
    font-size: 11px;
    line-height: 1;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--muted);
  }
  .field-label {
    position: absolute;
    left: 24px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .suggested-label {
    top: 325px;
  }
  .suggested-name {
    position: absolute;
    left: 25px;
    top: 349px;
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
    max-width: calc(100% - 170px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .detail-match {
    position: absolute;
    right: 24px;
    top: 340px;
    width: 116px;
    height: 26px;
    font-size: 11px;
  }
  .correct-label {
    top: 385px;
  }
  .select-wrap {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 406px;
    height: 44px;
  }
  .select {
    width: 100%;
    height: 100%;
    appearance: none;
    padding-right: 40px;
    cursor: pointer;
  }
  .select-chev {
    position: absolute;
    right: 14px;
    top: 14px;
    display: flex;
    color: var(--muted);
    pointer-events: none;
  }
  .save-btn {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 474px;
    height: 46px;
    font-size: 13px;
  }
  .info-icon {
    position: absolute;
    left: 26px;
    top: 545px;
    display: flex;
    color: var(--muted);
  }
  .info-text {
    position: absolute;
    left: 54px;
    right: 24px;
    top: 547px;
    font-size: 11px;
    line-height: 20px;
    color: var(--muted);
  }
  .detail-empty {
    position: absolute;
    inset: 60px 0 0;
  }

  @media (max-width: 1100px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
