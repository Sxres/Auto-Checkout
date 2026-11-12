<script>
  import Icon from '../../lib/Icon.svelte'
  import { app, go, startCheckout } from '../../lib/state.svelte.js'
  import Overview from './Overview.svelte'
  import ReviewQueue from './ReviewQueue.svelte'
  import Catalog from './Catalog.svelte'
  import Retraining from './Retraining.svelte'
  import Monitoring from './Monitoring.svelte'
  import Settings from './Settings.svelte'

  const nav = [
    { page: 'overview', label: 'Overview', icon: 'grid' },
    { page: 'review', label: 'Review queue', icon: 'inbox' },
    { page: 'catalog', label: 'Product catalog', icon: 'tag' },
    { page: 'retraining', label: 'Retraining', icon: 'refresh' },
    { page: 'monitoring', label: 'Monitoring', icon: 'activity' },
    { page: 'settings', label: 'Settings', icon: 'gear' },
  ]
  const titles = {
    overview: 'Overview',
    review: 'Review queue',
    catalog: 'Product catalog',
    retraining: 'Retraining',
    monitoring: 'Monitoring',
    settings: 'Settings',
  }

  let kioskMenu = $state(false)
</script>

<div class="shell">
  <!-- Sidebar -->
  <aside class="sidebar">
    <button class="selector" onclick={() => (kioskMenu = !kioskMenu)} aria-haspopup="menu">
      <span class="sel-icon"><Icon name="monitor" size={20} /></span>
      <span class="sel-name">{app.kioskName}</span>
      <span class="sel-chev"><Icon name="chevronDown" size={16} /></span>
    </button>
    {#if kioskMenu}
      <div class="kiosk-menu" role="menu">
        <button class="kiosk-opt" role="menuitem" onclick={() => (kioskMenu = false)}>
          <Icon name="check" size={14} />
          <span>{app.kioskName}</span>
        </button>
      </div>
    {/if}

    <p class="ws-label">Workspace</p>

    <nav class="nav">
      {#each nav as item}
        <button
          class="nav-item"
          class:active={app.page === item.page}
          aria-label={item.label}
          title={item.label}
          onclick={() => go('manager', item.page)}
        >
          <Icon name={item.icon} size={16} />
          <span class="nav-label">{item.label}</span>
          {#if item.page === 'review' && app.review.length > 0}
            <span class="nav-badge">{app.review.length}</span>
          {/if}
        </button>
      {/each}
    </nav>

    <div class="side-bottom">
      <div class="status-card" class:offline={!app.kioskStatus.online}>
        <span class="status-dot"></span>
        <div class="status-text">
          <span class="status-title">{app.kioskStatus.online ? 'Kiosk online' : 'Kiosk offline'}</span>
          <span class="status-sub">
            {app.kioskStatus.cameraConnected ? 'Camera connected' : 'Camera not connected'}
          </span>
        </div>
      </div>

      <div class="side-divider"></div>

      <div class="mgr-row">
        <span class="avatar"><Icon name="person" size={18} /></span>
        <div class="mgr-text">
          <span class="mgr-name">Manager</span>
          <span class="mgr-sub">Session active</span>
        </div>
      </div>
      <button class="signout" onclick={() => go('landing')}>Lock &amp; sign out</button>
    </div>
  </aside>

  <!-- Topbar -->
  <header class="topbar">
    <div class="crumb">
      <span class="crumb-ws">Workspace</span>
      <span class="crumb-sep">/</span>
      <span class="crumb-page">{titles[app.page]}</span>
    </div>
    <button class="btn-line customer-btn" onclick={startCheckout}>Open customer view</button>
  </header>

  <!-- Content -->
  <main class="content">
    {#if app.page === 'overview'}
      <Overview />
    {:else if app.page === 'review'}
      <ReviewQueue />
    {:else if app.page === 'catalog'}
      <Catalog />
    {:else if app.page === 'retraining'}
      <Retraining />
    {:else if app.page === 'monitoring'}
      <Monitoring />
    {:else}
      <Settings />
    {/if}
  </main>
</div>

<style>
  .shell {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
    grid-template-rows: 80px minmax(0, 1fr);
    animation: fadeIn 0.25s ease both;
  }

  .sidebar {
    grid-row: 1 / 3;
    position: relative;
    display: flex;
    flex-direction: column;
    padding: 33px 24px 24px;
    background: var(--dark);
    overflow-y: auto;
  }
  .selector {
    width: 100%;
    height: 48px;
    flex-shrink: 0;
    background: var(--dark2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    transition: filter 0.15s ease;
  }
  .selector:hover {
    filter: brightness(1.12);
  }
  .sel-icon {
    display: flex;
    margin-left: 8px;
    color: var(--surface);
  }
  .sel-name {
    margin-left: 13px;
    font-size: 13px;
    font-weight: 700;
    color: var(--surface);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sel-chev {
    margin-left: auto;
    margin-right: 9px;
    display: flex;
    color: var(--bg);
    flex-shrink: 0;
  }
  .kiosk-menu {
    position: absolute;
    left: 24px;
    top: 86px;
    width: 192px;
    background: var(--dark2);
    border: 1px solid #55574f;
    border-radius: 8px;
    padding: 4px;
    z-index: 30;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    animation: popIn 0.12s ease both;
  }
  .kiosk-opt {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 9px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    color: var(--surface);
  }
  .kiosk-opt:hover {
    background: rgba(255, 255, 255, 0.06);
  }

  .ws-label {
    margin-top: 35px;
    font-size: 11px;
    line-height: 1;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--bg);
  }

  .nav {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .nav-item {
    width: 100%;
    height: 46px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding-left: 16px;
    gap: 15px;
    border-radius: 8px;
    color: var(--bg);
    transition: background 0.15s ease;
  }
  .nav-item:hover:not(.active) {
    background: rgba(255, 255, 255, 0.05);
  }
  .nav-item.active {
    background: var(--red);
    color: var(--white);
  }
  .nav-label {
    font-size: 14px;
    font-weight: 500;
    color: var(--surface);
    white-space: nowrap;
  }
  .nav-item.active .nav-label {
    color: var(--white);
    font-weight: 600;
  }
  .nav-badge {
    margin-left: auto;
    margin-right: 14px;
    font-size: 13px;
    color: var(--bg);
  }
  .nav-item.active .nav-badge {
    color: var(--white);
  }

  .side-bottom {
    margin-top: auto;
    padding-top: 32px;
    display: flex;
    flex-direction: column;
  }
  .status-card {
    width: 100%;
    height: 72px;
    flex-shrink: 0;
    background: var(--dark2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px;
  }
  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--dot-green);
    animation: pulse 2.4s ease-in-out infinite;
    flex-shrink: 0;
  }
  .status-card.offline .status-dot {
    background: var(--cam-border);
    animation: none;
  }
  .status-text {
    display: flex;
    flex-direction: column;
    gap: 9px;
    min-width: 0;
  }
  .status-title {
    font-size: 12px;
    line-height: 1;
    font-weight: 700;
    color: var(--surface);
    white-space: nowrap;
  }
  .status-sub {
    font-size: 11px;
    line-height: 1;
    color: var(--bg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .side-divider {
    height: 1px;
    background: var(--dark2);
    margin: 23px 0;
    flex-shrink: 0;
  }
  .mgr-row {
    display: flex;
    align-items: center;
    gap: 13px;
  }
  .avatar {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--chip);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .mgr-text {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
  .mgr-name {
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
    color: var(--surface);
  }
  .mgr-sub {
    font-size: 11px;
    line-height: 1;
    color: var(--bg);
  }
  .signout {
    margin-top: 22px;
    margin-left: 53px;
    font-size: 12px;
    line-height: 1;
    color: var(--bg);
    text-align: left;
    transition: color 0.15s ease;
  }
  .signout:hover {
    color: var(--surface);
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 32px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .crumb {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 13px;
    line-height: 1;
    min-width: 0;
  }
  .crumb-ws,
  .crumb-sep {
    color: var(--muted);
  }
  .crumb-page {
    margin-left: 18px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .customer-btn {
    margin-left: auto;
    width: 214px;
    height: 40px;
    flex-shrink: 0;
    font-size: 12px;
  }

  .content {
    overflow-y: auto;
    padding: 0 32px 48px;
  }

  @media (max-width: 900px) {
    .shell {
      grid-template-columns: 200px minmax(0, 1fr);
    }
    .sidebar {
      padding: 24px 16px 20px;
    }
    .kiosk-menu {
      left: 16px;
      width: 168px;
    }
    .content {
      padding: 0 20px 32px;
    }
    .topbar {
      padding: 0 20px;
    }
    .customer-btn {
      width: auto;
      padding: 0 16px;
    }
  }
  @media (max-width: 640px) {
    .shell {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto minmax(0, 1fr);
    }
    .sidebar {
      grid-row: 1;
      flex-direction: row;
      flex-wrap: wrap;
      align-items: center;
      padding: 12px 16px;
      overflow: visible;
    }
    .selector {
      width: auto;
      flex: 1;
      min-width: 0;
      height: 40px;
    }
    .kiosk-menu {
      left: 16px;
      top: 58px;
    }
    .ws-label {
      display: none;
    }
    .nav {
      order: 3;
      width: 100%;
      margin-top: 10px;
      flex-direction: row;
      justify-content: space-between;
      gap: 4px;
    }
    .nav-item {
      position: relative;
      width: 44px;
      height: 40px;
      padding-left: 0;
      justify-content: center;
      gap: 0;
    }
    .nav-label {
      display: none;
    }
    .nav-badge {
      position: absolute;
      top: 2px;
      right: 4px;
      margin: 0;
      font-size: 10px;
    }
    .side-bottom {
      margin-top: 0;
      margin-left: 12px;
      padding-top: 0;
    }
    .status-card,
    .side-divider,
    .mgr-row {
      display: none;
    }
    .signout {
      margin: 0;
      white-space: nowrap;
    }
    .topbar {
      height: 56px;
      padding: 0 16px;
    }
    .crumb-ws,
    .crumb-sep {
      display: none;
    }
    .crumb-page {
      margin-left: 0;
    }
    .customer-btn {
      height: 36px;
      padding: 0 12px;
      font-size: 11px;
    }
    .content {
      padding: 0 16px 32px;
    }
  }
</style>
