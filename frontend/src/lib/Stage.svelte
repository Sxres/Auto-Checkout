<script>
  let { children } = $props()
</script>

<div class="viewport">
  {@render children()}
</div>

<style>
  .viewport {
    position: fixed;
    inset: 0;
    background: var(--bg);
    overflow: hidden;
  }
</style>
