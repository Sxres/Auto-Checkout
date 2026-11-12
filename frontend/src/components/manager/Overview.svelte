<script>
  import Icon from '../../lib/Icon.svelte'
  import PageHead from './PageHead.svelte'
  import { app, go } from '../../lib/state.svelte.js'

  const activeAlerts = $derived(app.alerts.filter((a) => a.status === 'Active').length)

  const stats = $derived([
    { label: 'Checkouts today', value: String(app.metrics.checkoutsToday), delta: 'No data yet', tone: 'muted', icon: 'basket' },
    { label: 'Recognition rate', value: app.metrics.recognitionRate ?? '—', delta: 'No data yet', tone: 'muted', icon: 'eye' },
    {
      label: 'Waiting for review',
      value: String(app.review.length),
      delta: app.review.length ? 'Needs a human check' : 'Queue is clear',
      tone: app.review.length ? 'amber' : 'muted',
      icon: 'inbox',
    },
    {
      label: 'Avg. checkout time',
      value: app.metrics.avgCheckoutSeconds != null ? `${app.metrics.avgCheckoutSeconds}s` : '—',
      delta: 'No data yet',
      tone: 'muted',
      icon: 'clock',
    },
  ])

  const live = $derived(app.versions.find((v) => v.status === 'Live'))
  const readyCount = $derived(app.products.filter((p) => p.status === 'Ready').length)
  const needCount = $derived(app.products.length - readyCount)
  const statusRows = $derived([
    {
      icon: 'camera',
      label: 'Camera',
      value: app.kioskStatus.cameraConnected ? 'Connected' : 'Not connected',
      ok: app.kioskStatus.cameraConnected,
    },
    { icon: 'box', label: 'Current version', value: live?.v ?? '—', ok: !!live },
    {
      icon: 'checkCircle',
      label: 'Products ready',
      value: `${readyCount} of ${app.products.length}`,
      ok: app.products.length > 0 && needCount === 0,
    },
  ])
  const statusNote = $derived(
    app.products.length === 0
      ? 'No products in the catalog yet.'
      : needCount > 0
        ? `${needCount} ${needCount === 1 ? 'product needs' : 'products need'} more images.`
        : 'All products have enough images.',
  )

  const heights = $derived(app.metrics.chart.heights)
  const chartMax = $derived(heights.length ? Math.max(...heights, 1) : 1)
  const peakIndex = $derived(heights.indexOf(Math.max(...heights)))
</script>

<div class="page">
  <PageHead title="Overview" subtitle="A clear view of today's checkout activity.">
    <button class="btn-line health-btn" onclick={() => go('manager', 'monitoring')}>
      <span>System health</span>
      <span class="health-alert" class:quiet={activeAlerts === 0}>
        {activeAlerts === 0 ? 'No active alerts' : `${activeAlerts} active ${activeAlerts === 1 ? 'alert' : 'alerts'}`}
      </span>
      <Icon name="chevronRight" size={14} />
    </button>
    <button class="btn-red review-btn" onclick={() => go('manager', 'review')}>
      Review {app.review.length} items
    </button>
  </PageHead>

  <!-- Stat cards -->
  <div class="stats">
    {#each stats as s}
      <div class="card stat">
        <span class="stat-label">{s.label}</span>
        <span class="stat-value tnum">{s.value}</span>
        <span class="stat-delta {s.tone}">{s.delta}</span>
        <span class="icon-chip stat-icon"><Icon name={s.icon} size={14} /></span>
      </div>
    {/each}
  </div>

  <div class="mid">
    <!-- Chart -->
    <div class="card chart-card">
      <div class="chart-head">
        <span class="chart-title">Checkouts over time</span>
        <span class="chart-range">Today</span>
      </div>
      {#if heights.length}
        <div class="plot">
          <div class="y-axis tnum">
            <span>{chartMax}</span>
            <span>{Math.round(chartMax / 2)}</span>
            <span>0</span>
          </div>
          <div class="plot-area">
            {#each [0, 1, 2] as i}
              <div class="gridline" style="top: {i * 50}%"></div>
            {/each}
            <div class="bars">
              {#each heights as h, i}
                <div
                  class="bar"
                  class:dark={i === peakIndex}
                  style="height: {(h / chartMax) * 100}%; animation-delay: {i * 0.03}s"
                ></div>
              {/each}
            </div>
          </div>
        </div>
        <div class="x-labels tnum">
          {#each app.metrics.chart.labels as lab}
            <span>{lab}</span>
          {/each}
        </div>
        <p class="chart-caption tnum">{app.metrics.checkoutsToday} completed checkouts today</p>
      {:else}
        <div class="empty-state chart-empty">
          <span class="icon-chip"><Icon name="activity" size={18} /></span>
          <p class="empty-title">No checkout activity yet.</p>
          <p class="empty-sub">Checkouts will chart here throughout the day.</p>
        </div>
      {/if}
    </div>

    <!-- Kiosk status -->
    <div class="card status-card">
      <span class="card-title">Kiosk status</span>
      <span class="pill online-pill {app.kioskStatus.online ? 'pill-green' : 'pill-gray'}">
        {app.kioskStatus.online ? 'Online' : 'Offline'}
      </span>
      {#each statusRows as r, i}
        <div class="status-row" style="top: {70 + i * 46}px">
          <span class="row-icon" class:ok={r.ok}><Icon name={r.icon} size={16} /></span>
          <span class="row-label">{r.label}</span>
          <span class="row-value tnum">{r.value}</span>
        </div>
      {/each}
      <div class="divider status-divider"></div>
      <span class="status-note">{statusNote}</span>
      <button class="btn-line catalog-btn" onclick={() => go('manager', 'catalog')}>View product catalog</button>
    </div>
  </div>

  <!-- Recent checkouts -->
  <div class="card recent-card">
    <span class="card-title">Recent checkouts</span>
    <div class="table">
      <div class="trow thead">
        {#each ['Checkout', 'Time', 'Items', 'Duration', 'Status'] as h}
          <span class="th">{h}</span>
        {/each}
      </div>
      {#each app.checkouts as c}
        <div class="trow">
          <span class="td bold tnum">{c.id}</span>
          <span class="td tnum">{c.time}</span>
          <span class="td">{c.items}</span>
          <span class="td tnum">{c.duration}</span>
          <span class="td status-text {c.status === 'Completed' ? 'green' : 'amber'}">{c.status}</span>
        </div>
      {:else}
        <div class="empty-state table-empty">
          <span class="icon-chip"><Icon name="basket" size={18} /></span>
          <p class="empty-title">No checkouts yet.</p>
          <p class="empty-sub">Completed checkouts will appear here.</p>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .page {
    animation: fadeIn 0.25s ease both;
  }

  .health-btn {
    height: 42px;
    padding: 0 16px;
    font-size: 12px;
    gap: 8px;
  }
  .health-alert {
    color: var(--amber);
    font-weight: 600;
  }
  .health-alert.quiet {
    color: var(--muted);
  }
  .review-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 12px;
    white-space: nowrap;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 24px;
  }
  .stat {
    position: relative;
    height: 128px;
  }
  .stat-label {
    position: absolute;
    left: 25px;
    top: 17px;
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .stat-value {
    position: absolute;
    left: 25px;
    top: 49px;
    font-size: 24px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
  .stat-delta {
    position: absolute;
    left: 25px;
    top: 95px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    line-height: 1;
    font-weight: 600;
  }
  .stat-delta.green {
    color: var(--green);
  }
  .stat-delta.amber {
    color: var(--amber);
  }
  .stat-delta.muted {
    color: var(--muted);
    font-weight: 500;
  }
  .stat-icon {
    position: absolute;
    right: 20px;
    top: 19px;
  }

  .mid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 376px;
    gap: 24px;
    margin: 24px 0;
  }

  .card-title {
    position: absolute;
    left: 25px;
    top: 19px;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }

  .chart-card {
    position: relative;
    height: 298px;
    display: flex;
    flex-direction: column;
    padding: 19px 25px 22px;
  }
  .chart-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }
  .chart-title {
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
  }
  .chart-range {
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
  }
  .chart-empty {
    flex: 1;
  }
  .plot {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 12px;
    margin-top: 20px;
  }
  .y-axis {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-end;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
    width: 24px;
    flex-shrink: 0;
  }
  .plot-area {
    position: relative;
    flex: 1;
    min-width: 0;
  }
  .gridline {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: var(--border);
  }
  .bars {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 8px;
    padding: 0 4px;
  }
  .bar {
    flex: 1;
    max-width: 32px;
    min-width: 4px;
    background: var(--red);
    border-radius: 4px 4px 0 0;
    animation: fadeUp 0.4s ease both;
  }
  .bar.dark {
    background: var(--ink);
  }
  .x-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    padding-left: 36px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .chart-caption {
    margin-top: 14px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }

  .status-card {
    position: relative;
    height: 298px;
  }
  .online-pill {
    position: absolute;
    right: 24px;
    top: 22px;
    height: 26px;
    padding: 0 16px;
    font-size: 11px;
  }
  .status-row {
    position: absolute;
    left: 25px;
    right: 25px;
    height: 16px;
    display: flex;
    align-items: center;
  }
  .row-icon {
    display: flex;
    color: var(--muted);
  }
  .row-icon.ok {
    color: var(--green);
  }
  .row-label {
    margin-left: 15px;
    font-size: 13px;
    color: var(--muted);
  }
  .row-value {
    margin-left: auto;
    font-size: 13px;
    font-weight: 700;
    color: var(--ink);
  }
  .status-divider {
    position: absolute;
    left: 25px;
    right: 25px;
    top: 197px;
  }
  .status-note {
    position: absolute;
    left: 25px;
    right: 25px;
    top: 211px;
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .catalog-btn {
    position: absolute;
    left: 24px;
    right: 24px;
    top: 240px;
    height: 36px;
    font-size: 13px;
  }

  .recent-card {
    position: relative;
    min-height: 218px;
    padding: 19px 25px 20px;
  }
  .recent-card .card-title {
    position: static;
    display: block;
  }
  .table {
    margin-top: 25px;
  }
  .trow {
    display: grid;
    grid-template-columns: 1.7fr 1.15fr 1.05fr 1fr 1fr;
    align-items: center;
    gap: 12px;
    height: 39px;
  }
  .trow + .trow {
    border-top: 1px solid var(--border);
  }
  .thead {
    height: 32px;
  }
  .th {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .td {
    font-size: 13px;
    line-height: 1;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .td.bold {
    font-weight: 700;
  }
  .status-text {
    font-size: 12px;
    font-weight: 700;
  }
  .status-text.green {
    color: var(--green);
  }
  .status-text.amber {
    color: var(--amber);
  }
  .table-empty {
    padding: 20px 24px 12px;
  }

  @media (max-width: 1200px) {
    .stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .mid {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 640px) {
    .stats {
      grid-template-columns: 1fr;
    }
    .trow {
      grid-template-columns: 1.4fr 1fr 1fr;
    }
    .trow > :nth-child(4),
    .trow > :nth-child(5) {
      display: none;
    }
  }
</style>
