<script>
  let { title, subtitle, children } = $props()
</script>

<div class="head">
  <div class="head-text">
    <h1 class="title">{title}</h1>
    <p class="subtitle">{subtitle}</p>
  </div>
  {#if children}
    <div class="actions">{@render children()}</div>
  {/if}
</div>

<style>
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    padding-top: 31px;
    margin-bottom: 36px;
  }
  .head-text {
    min-width: 0;
  }
  .title {
    font-size: 30px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: var(--ink);
  }
  .subtitle {
    margin-top: 15px;
    font-size: 14px;
    line-height: 1;
    color: var(--muted);
  }
  .actions {
    margin-top: 5px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  @media (max-width: 760px) {
    .head {
      flex-direction: column;
      gap: 16px;
    }
    .actions {
      margin-top: 0;
      justify-content: flex-start;
    }
  }
</style>
