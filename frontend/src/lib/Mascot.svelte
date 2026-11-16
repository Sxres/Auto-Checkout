<script>
  let { mood = 'idle', size = 16, bubble = '', dark = false } = $props()

  let blink = $state(false)
  let glance = $state(0)

  $effect(() => {
    if (mood !== 'idle' && mood !== 'happy') return
    let timer
    const schedule = () => {
      timer = setTimeout(() => {
        blink = true
        timer = setTimeout(() => {
          blink = false
          schedule()
        }, 150)
      }, 2400 + Math.random() * 2600)
    }
    schedule()
    return () => clearTimeout(timer)
  })

  $effect(() => {
    if (mood !== 'scan') return
    const timer = setInterval(() => (glance = (glance + 1) % 4), 650)
    return () => clearInterval(timer)
  })

  const eyes = $derived(
    mood === 'scan'
      ? ['│ o o │', '│o  o │', '│ o o │', '│ o  o│'][glance]
      : mood === 'oops'
        ? '│ > < │'
        : (mood === 'idle' || mood === 'happy') && blink
          ? '│ - - │'
          : '│ ^ ^ │',
  )
  const mouth = $derived(
    mood === 'scan'
      ? '│  o  │'
      : mood === 'oops'
        ? '│  ~  │'
        : mood === 'happy' || mood === 'cheer'
          ? '│  ▽  │'
          : '│  ◡  │',
  )
  const lines = $derived(
    [mood === 'cheer' ? '╲ ╭─────╮ ╱' : '╭─────╮', eyes, mouth, '╰─────╯'].join('\n'),
  )
</script>

<div class="mascot" class:dark style="font-size: {size}px">
  {#if bubble}
    {#key bubble}
      <p class="bubble">{bubble}</p>
    {/key}
  {/if}
  <div class="figure" class:scan={mood === 'scan'} class:cheer={mood === 'cheer'}>
    <pre aria-hidden="true">{lines}</pre>
    {#if mood === 'cheer'}
      <span class="spark s1" aria-hidden="true">✦</span>
      <span class="spark s2" aria-hidden="true">+</span>
      <span class="spark s3" aria-hidden="true">✦</span>
      <span class="spark s4" aria-hidden="true">·</span>
    {/if}
  </div>
</div>

<style>
  .mascot {
    --bub-bg: var(--surface);
    --bub-border: var(--border);
    --bub-ink: var(--ink);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
  }
  .mascot.dark {
    --bub-bg: var(--dark2);
    --bub-border: #55574f;
    --bub-ink: var(--surface);
  }

  .bubble {
    position: relative;
    max-width: 280px;
    padding: 9px 14px;
    background: var(--bub-bg);
    border: 1px solid var(--bub-border);
    border-radius: 12px;
    font-size: max(13px, 0.8em);
    line-height: 1.4;
    font-weight: 500;
    text-align: center;
    color: var(--bub-ink);
    animation: popIn 0.25s ease both;
  }
  .bubble::after {
    content: '';
    position: absolute;
    bottom: -5.5px;
    left: 50%;
    width: 10px;
    height: 10px;
    transform: translateX(-50%) rotate(45deg);
    background: var(--bub-bg);
    border-right: 1px solid var(--bub-border);
    border-bottom: 1px solid var(--bub-border);
  }

  .figure {
    position: relative;
    animation: float 4s ease-in-out infinite;
  }
  .figure.scan {
    animation: inspect 2.6s ease-in-out infinite;
  }
  .figure.cheer {
    animation: bounce 1.1s ease-in-out infinite;
  }
  pre {
    font-family: var(--mono);
    line-height: 1.3;
    text-align: center;
    color: var(--ink);
  }
  .mascot.dark pre {
    color: var(--surface);
  }

  .spark {
    position: absolute;
    font-size: 0.85em;
    line-height: 1;
    animation: twinkle 1.7s ease-in-out infinite;
  }
  .s1 {
    top: -0.9em;
    left: -1.1em;
    color: var(--red);
  }
  .s2 {
    top: -0.5em;
    right: -1.2em;
    color: var(--green);
    animation-delay: 0.45s;
  }
  .s3 {
    bottom: 0.4em;
    left: -1.5em;
    color: var(--amber);
    animation-delay: 0.9s;
  }
  .s4 {
    bottom: -0.6em;
    right: -0.9em;
    color: var(--muted);
    animation-delay: 1.3s;
  }

  @keyframes float {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-4px);
    }
  }
  @keyframes inspect {
    0%,
    100% {
      transform: rotate(0deg);
    }
    25% {
      transform: rotate(-2.5deg);
    }
    75% {
      transform: rotate(2.5deg);
    }
  }
  @keyframes bounce {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-7px);
    }
  }
  @keyframes twinkle {
    0%,
    100% {
      opacity: 0;
      transform: scale(0.5) rotate(0deg);
    }
    50% {
      opacity: 1;
      transform: scale(1) rotate(25deg);
    }
  }
</style>
