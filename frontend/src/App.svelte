<script>
  import Stage from './lib/Stage.svelte'
  import Icon from './lib/Icon.svelte'
  import Landing from './components/Landing.svelte'
  import Shell from './components/manager/Shell.svelte'
  import Kiosk from './components/kiosk/Kiosk.svelte'
  import Complete from './components/Complete.svelte'
  import { app, dismissToast, loadWorkspace } from './lib/state.svelte.js'

  loadWorkspace()
</script>

<Stage>
  {#if app.view === 'landing'}
    <Landing />
  {:else if app.view === 'manager'}
    <Shell />
  {:else if app.view === 'kiosk'}
    <Kiosk />
  {:else}
    <Complete />
  {/if}

  {#if app.toast}
    <div class="toast" role="status">
      <span>{app.toast.message}</span>
      {#if app.toast.action}
        <button
          class="toast-action"
          onclick={() => {
            app.toast.action.run()
            dismissToast()
          }}>{app.toast.action.label}</button
        >
      {/if}
      <button class="toast-close" onclick={dismissToast} aria-label="Dismiss">
        <Icon name="x" size={14} />
      </button>
    </div>
  {/if}
</Stage>

<style>
  .toast {
    position: absolute;
    left: 50%;
    bottom: 28px;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 16px;
    background: var(--dark);
    color: var(--surface);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    box-shadow: 0 8px 24px rgba(23, 23, 23, 0.28);
    z-index: 200;
    animation: fadeUp 0.22s ease both;
  }
  .toast-action {
    color: var(--white);
    font-weight: 700;
    font-size: 13px;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .toast-close {
    display: inline-flex;
    color: var(--bg);
    opacity: 0.8;
  }
  .toast-close:hover {
    opacity: 1;
  }
</style>
