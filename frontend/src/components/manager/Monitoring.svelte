<script>
  import Icon from '../../lib/Icon.svelte'
  import PageHead from './PageHead.svelte'
  import { app, toast } from '../../lib/state.svelte.js'

  const mon = $derived(app.monitoring)
  const activeCount = $derived(app.alerts.filter((a) => a.status === 'Active').length)

  const ms = (n) => (n != null ? `${n} ms` : '—')
  const pct = (n) => (n != null ? `${n}%` : '—')

  const cards = $derived([
    {
      title: 'Kiosk & camera',
      sub: app.kioskName,
      badge: mon?.kiosk.cameraConnected == null ? 'No data' : mon.kiosk.cameraConnected ? 'Online' : 'Offline',
      tone: mon?.kiosk.cameraConnected == null ? 'gray' : mon.kiosk.cameraConnected ? 'green' : 'gray',
      rows: [
        ['Camera connection', mon?.kiosk.cameraConnected == null ? '—' : mon.kiosk.cameraConnected ? 'Connected' : 'Not connected'],
        ['Checkout failures (24h)', mon?.kiosk.failures24h ?? '—'],
      ],
    },
    {
      title: 'Application API',
      sub: 'Last 15 minutes',
      badge: mon?.api.healthy == null ? 'No data' : mon.api.healthy ? 'Healthy' : 'Down',
      tone: mon?.api.healthy == null ? 'gray' : mon.api.healthy ? 'green' : 'amber',
      rows: [
        ['Request latency (p95)', ms(mon?.api.latencyMs)],
        ['Request error rate', pct(mon?.api.errorRate)],
      ],
    },
    {
      title: 'Model inference',
      sub: 'Last 15 minutes',
      badge: mon?.model.ready == null ? 'No data' : mon.model.ready ? 'Ready' : 'Needs attention',
      tone: mon?.model.ready == null ? 'gray' : mon.model.ready ? 'green' : 'amber',
      rows: [
        ['Inference latency (p95)', ms(mon?.model.latencyMs)],
        ['Low-confidence rate', pct(mon?.model.lowConfidenceRate)],
      ],
    },
  ])

  function resolve(a) {
    if (a.status !== 'Active') return
    a.status = 'Resolved'
    a.desc = 'Threshold returned to normal.'
    toast(`Marked “${a.title}” as resolved.`)
  }
</script>

<div class="page">
  <PageHead title="Monitoring" subtitle="System health and recent alerts for the checkout stack.">
    <span class="pill pill-amber alert-count" class:invisible={activeCount === 0}>
      {activeCount} active alert{activeCount === 1 ? '' : 's'}
    </span>
  </PageHead>

  <h2 class="section-title">System health</h2>

  <div class="health-grid">
    {#each cards as c}
      <div class="card health-card">
        <span class="health-title">{c.title}</span>
        <span class="pill health-badge pill-{c.tone}">{c.badge}</span>
        <span class="health-sub">{c.sub}</span>
        {#each c.rows as row, j}
          <span class="row-label" style="top: {94 + j * 30}px">{row[0]}</span>
          <span class="row-value tnum" style="top: {94 + j * 30}px">{row[1]}</span>
        {/each}
      </div>
    {/each}
  </div>

  <div class="card alerts-card">
    <div class="alerts-head">
      <h2 class="alerts-title">Recent alerts</h2>
      <span class="alerts-count tnum">{app.alerts.length} alerts</span>
    </div>
    <p class="alerts-sub">Events from the last 24 hours.</p>

    {#if app.alerts.length > 0}
      <div class="table">
        <div class="trow thead">
          {#each ['Alert', 'Source', 'Detected', 'Status'] as h}
            <span class="th">{h}</span>
          {/each}
        </div>
        {#each app.alerts as a}
          <div class="trow">
            <span class="alert-main">
              <span class="alert-title">{a.title}</span>
              <span class="alert-desc">{a.desc}</span>
            </span>
            <span class="alert-cell">{a.source}</span>
            <span class="alert-cell col-detected">{a.detected}</span>
            {#if a.status === 'Active'}
              <button class="pill pill-amber alert-badge clickable" onclick={() => resolve(a)} title="Mark as resolved">
                Active
              </button>
            {:else}
              <span class="pill pill-green alert-badge">Resolved</span>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state alerts-empty">
        <span class="icon-chip"><Icon name="checkCircle" size={18} /></span>
        <p class="empty-title">No alerts in the last 24 hours.</p>
        <p class="empty-sub">Camera, API, and model events will show up here.</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .page {
    animation: fadeIn 0.25s ease both;
  }
  .alert-count {
    height: 26px;
    padding: 0 13px;
    font-size: 12px;
    margin-top: 15px;
  }
  .alert-count.invisible {
    visibility: hidden;
  }
  .section-title {
    margin: 2px 0 14px;
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
  }

  .health-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 24px;
  }
  .health-card {
    position: relative;
    height: 164px;
  }
  .health-title {
    position: absolute;
    left: 21px;
    top: 26px;
    font-size: 17px;
    line-height: 1;
    font-weight: 700;
    max-width: calc(100% - 130px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .health-badge {
    position: absolute;
    right: 21px;
    top: 30px;
    height: 26px;
    padding: 0 12px;
    font-size: 12px;
    white-space: nowrap;
  }
  .health-sub {
    position: absolute;
    left: 21px;
    top: 51px;
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .row-label {
    position: absolute;
    left: 21px;
    font-size: 14px;
    line-height: 1;
    color: var(--muted);
  }
  .row-value {
    position: absolute;
    right: 21px;
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
  }

  .alerts-card {
    min-height: 358px;
    margin-top: 26px;
    display: flex;
    flex-direction: column;
    padding: 23px 24px 24px;
  }
  .alerts-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .alerts-title {
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
  }
  .alerts-count {
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .alerts-sub {
    margin-top: 10px;
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .table {
    margin-top: 21px;
  }
  .trow {
    display: grid;
    grid-template-columns: 2.6fr 1fr 1fr 110px;
    align-items: center;
    gap: 12px;
    min-height: 75px;
    padding: 12px 0;
  }
  .trow + .trow {
    border-top: 1px solid var(--border);
  }
  .thead {
    min-height: 0;
    height: 29px;
    padding: 0;
    border-bottom: 1px solid var(--border);
  }
  .th {
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .alert-main {
    display: flex;
    flex-direction: column;
    gap: 9px;
    min-width: 0;
  }
  .alert-title {
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
  }
  .alert-desc {
    font-size: 13px;
    line-height: 1.3;
    color: var(--muted);
  }
  .alert-cell {
    font-size: 13px;
    line-height: 1;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .alert-badge {
    height: 26px;
    padding: 0 14px;
    font-size: 12px;
    font-weight: 700;
    justify-self: start;
    white-space: nowrap;
  }
  .alert-badge.clickable {
    cursor: pointer;
    transition: filter 0.12s ease;
  }
  .alert-badge.clickable:hover {
    filter: brightness(0.94);
  }
  .alerts-empty {
    flex: 1;
    padding: 40px 24px;
  }

  @media (max-width: 1100px) {
    .health-grid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 640px) {
    .trow {
      grid-template-columns: 2fr 1fr 90px;
    }
    .col-detected,
    .thead > :nth-child(3) {
      display: none;
    }
  }
</style>
