<script>
  let { kind, size = 24, width, height } = $props()
  const w = $derived(width ?? size)
  const h = $derived(height ?? size)
</script>

<svg
  width={w}
  height={h}
  viewBox="0 0 64 64"
  preserveAspectRatio="none"
  fill="currentColor"
  aria-hidden="true"
>
  {#if kind === 'milk'}
    <rect x="24" y="3" width="16" height="6" rx="2" />
    <rect x="26" y="9" width="12" height="9" />
    <path d="M22 17h20l4 8v30a5 5 0 0 1-5 5H23a5 5 0 0 1-5-5V25z" />
    <rect x="18" y="34" width="28" height="11" fill-opacity="0.22" />
  {:else if kind === 'carton'}
    <path d="M17 24 32 9l15 15v34a2 2 0 0 1-2 2H19a2 2 0 0 1-2-2z" />
    <path d="M17 24h30" stroke="currentColor" stroke-opacity="0.4" stroke-width="2" fill="none" />
    <path d="M32 9v15" stroke="currentColor" stroke-opacity="0.25" stroke-width="2" fill="none" />
    <rect x="17" y="36" width="30" height="11" fill-opacity="0.25" />
  {:else if kind === 'apple'}
    <path d="M32 20c-4-7-14-8-18 0-4 8-2 24 8 31 4 3 8 2 10-1 2 3 6 4 10 1 10-7 12-23 8-31-4-8-14-7-18 0z" />
    <path d="M32 18c0-6 2-9 5-11" stroke="currentColor" stroke-width="3" stroke-linecap="round" fill="none" />
    <path d="M37 12c5-4 10-3 11 0-4 3-8 3-11 0z" />
  {:else if kind === 'water'}
    <rect x="26" y="3" width="12" height="7" rx="2" />
    <rect x="27" y="10" width="10" height="6" />
    <path d="M23 15h18c3 6 5 10 5 16v24a5 5 0 0 1-5 5H23a5 5 0 0 1-5-5V31c0-6 2-10 5-16z" />
    <rect x="18" y="34" width="28" height="10" fill-opacity="0.22" />
  {:else if kind === 'bar'}
    <path d="M6 28 1 24v17l5-4z" />
    <path d="m58 28 5-4v17l-5-4z" />
    <rect x="6" y="24" width="52" height="17" rx="4" />
    <path d="M24 24l-6 17M40 24l-6 17" stroke="currentColor" stroke-opacity="0.3" stroke-width="3" fill="none" />
  {:else if kind === 'chips'}
    <rect x="17" y="6" width="30" height="7" rx="2" />
    <path d="M19 13h26l4 39a4 4 0 0 1-4 4H19a4 4 0 0 1-4-4z" />
    <ellipse cx="32" cy="35" rx="10" ry="8" fill-opacity="0.22" />
  {:else if kind === 'pear'}
    <path d="M32 14c1 6 3 9 7 13 6 6 8 14 4 21-3 6-8 9-11 9s-8-3-11-9c-4-7-2-15 4-21 4-4 6-7 7-13z" />
    <path d="M32 14c0-5 1-8 4-10" stroke="currentColor" stroke-width="3" stroke-linecap="round" fill="none" />
  {:else if kind === 'juice'}
    <rect x="25" y="3" width="14" height="6" rx="2" />
    <rect x="27" y="9" width="10" height="7" />
    <path d="M21 16h22c2 5 4 9 4 14v25a5 5 0 0 1-5 5H22a5 5 0 0 1-5-5V30c0-5 2-9 4-14z" />
    <rect x="17" y="32" width="30" height="13" fill-opacity="0.22" />
  {:else if kind === 'banana'}
    <path d="M14 20c0 20 14 32 34 30 2 0 3-3 1-4-17 0-29-10-30-26 0-3-5-3-5 0z" />
  {/if}
</svg>
