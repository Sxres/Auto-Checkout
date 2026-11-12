<script>
  import Icon from './Icon.svelte'
  import { focusDialog } from './dialog.js'
  let { title, width = 460, children, footer, onclose } = $props()

  $effect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onclose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
</script>

<div
  class="scrim"
  onclick={(event) => event.target === event.currentTarget && onclose?.()}
  role="presentation"
>
  <div
    class="modal card"
    style="width: {width}px"
    role="dialog"
    aria-modal="true"
    aria-label={title}
    tabindex="-1"
    use:focusDialog
  >
    <div class="modal-head">
      <h2 class="modal-title">{title}</h2>
      <button class="modal-close" onclick={onclose} aria-label="Close">
        <Icon name="x" size={18} />
      </button>
    </div>
    <div class="modal-body">{@render children()}</div>
    {#if footer}
      <div class="modal-footer">{@render footer()}</div>
    {/if}
  </div>
</div>

<style>
  .scrim {
    position: fixed;
    inset: 0;
    background: rgba(23, 23, 23, 0.48);
    display: grid;
    place-items: center;
    z-index: 100;
    animation: fadeIn 0.18s ease both;
  }
  .modal {
    padding: 28px 32px 32px;
    max-width: calc(100vw - 48px);
    max-height: calc(100vh - 48px);
    overflow-y: auto;
    box-shadow: 0 18px 48px rgba(23, 23, 23, 0.3);
    animation: popIn 0.2s ease both;
  }
  .modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }
  .modal-title {
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
  }
  .modal-close {
    display: flex;
    color: var(--muted);
    padding: 4px;
    border-radius: 6px;
  }
  .modal-close:hover {
    color: var(--ink);
    background: var(--chip);
  }
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 26px;
  }
</style>
