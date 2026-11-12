<script>
  let { value = false, onchange, label = 'Toggle' } = $props()
</script>

<button
  class="toggle"
  class:on={value}
  role="switch"
  aria-checked={value}
  aria-label={label}
  onclick={() => onchange?.(!value)}
>
  <span class="knob"></span>
</button>

<style>
  .toggle {
    position: relative;
    width: 40px;
    height: 24px;
    border-radius: 12px;
    background: var(--border);
    transition: background 0.18s ease;
    flex-shrink: 0;
  }
  .toggle.on {
    background: var(--ink);
  }
  .knob {
    position: absolute;
    top: 4px;
    left: 4px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--surface);
    transition: left 0.18s ease;
  }
  .toggle.on .knob {
    left: 20px;
  }
</style>
