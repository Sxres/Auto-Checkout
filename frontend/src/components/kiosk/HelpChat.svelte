<script>
  import { onDestroy } from 'svelte'
  import Icon from '../../lib/Icon.svelte'
  import Mascot from '../../lib/Mascot.svelte'
  import { focusDialog } from '../../lib/dialog.js'
  import { app, toast } from '../../lib/state.svelte.js'

  const GREETING = "Hi, I'm Byte! What can I help you with?"

  const REPLIES = [
    {
      q: 'How does checkout work?',
      a: "Just place your items in view of the camera — I'll recognize them automatically and add them to your basket on the right. When you're done, tap Review & finish.",
    },
    {
      q: "My item wasn't recognized",
      a: "Turn the item so its label faces the camera and give it a moment. One item at a time works best. If it still isn't recognized, call a team member over.",
    },
    {
      q: 'Change or remove an item',
      a: 'Use + and − in your basket to change quantities, or Remove to take an item out. Start over at the top left clears the whole basket.',
    },
    {
      q: 'Something else',
      a: "I'm still learning the ropes! For anything else, call a team member over and they'll help you out.",
    },
  ]

  let messages = $state([{ from: 'byte', text: GREETING }])
  let typing = $state(false)
  let staffCalled = $state(false)
  let logEl = $state()
  let replyTimer

  onDestroy(() => clearTimeout(replyTimer))

  $effect(() => {
    messages.length
    typing
    if (logEl) logEl.scrollTop = logEl.scrollHeight
  })

  function ask(reply) {
    if (typing) return
    messages.push({ from: 'you', text: reply.q })
    typing = true
    replyTimer = setTimeout(() => {
      messages.push({ from: 'byte', text: reply.a })
      typing = false
    }, 700)
  }

  function callStaff() {
    if (staffCalled) return
    staffCalled = true
    messages.push({
      from: 'byte',
      text: "Done! I've let the team know — someone will be with you in a moment.",
    })
    toast('Staff notified — someone is on their way.')
  }

  const mood = $derived(typing ? 'scan' : staffCalled ? 'happy' : 'idle')
</script>

<div
  class="help-chat"
  role="dialog"
  aria-label="Help from Byte"
  tabindex="-1"
  use:focusDialog
>
  <div class="chat-head">
    <Mascot {mood} size={12} />
    <div class="chat-id">
      <div class="chat-name">Byte</div>
      <div class="chat-role">Kiosk assistant</div>
    </div>
    <button class="chat-close" onclick={() => (app.modal = null)} aria-label="Close help">
      <Icon name="x" size={15} />
    </button>
  </div>

  <div class="chat-log" bind:this={logEl}>
    {#each messages as m, i (i)}
      <div class="msg" class:you={m.from === 'you'}>{m.text}</div>
    {/each}
    {#if typing}
      <div class="msg typing" aria-label="Byte is typing">
        <span class="tdot"></span><span class="tdot"></span><span class="tdot"></span>
      </div>
    {/if}
  </div>

  <div class="chat-chips">
    {#each REPLIES as r (r.q)}
      <button class="chip" disabled={typing} onclick={() => ask(r)}>{r.q}</button>
    {/each}
  </div>

  <div class="chat-foot">
    <button
      class="btn-line staff-call"
      class:called={staffCalled}
      disabled={staffCalled}
      onclick={callStaff}
    >
      <Icon name={staffCalled ? 'check' : 'person'} size={16} />
      {staffCalled ? 'Staff notified — on their way' : 'Call staff over'}
    </button>
  </div>
</div>

<style>
  .help-chat {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 16px 40px rgba(23, 23, 23, 0.32);
    overflow: hidden;
    outline: none;
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .chat-id {
    min-width: 0;
  }
  .chat-name {
    font-size: 14px;
    font-weight: 700;
  }
  .chat-role {
    font-size: 11px;
    font-weight: 500;
    color: var(--muted);
  }
  .chat-close {
    margin-left: auto;
    display: inline-flex;
    padding: 6px;
    border-radius: 8px;
    color: var(--muted);
    transition: background 0.15s ease, color 0.15s ease;
  }
  .chat-close:hover {
    background: var(--chip);
    color: var(--ink);
  }

  .chat-log {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 14px;
    scroll-behavior: smooth;
  }
  .msg {
    max-width: 86%;
    padding: 9px 12px;
    border-radius: 12px 12px 12px 4px;
    background: var(--chip);
    font-size: 13px;
    line-height: 1.45;
    animation: fadeUp 0.2s ease both;
  }
  .msg.you {
    align-self: flex-end;
    border-radius: 12px 12px 4px 12px;
    background: var(--ink);
    color: var(--surface);
  }
  .msg.typing {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 12px 14px;
    align-self: flex-start;
  }
  .tdot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--muted);
    animation: typingBounce 1s ease-in-out infinite;
  }
  .tdot:nth-child(2) {
    animation-delay: 0.15s;
  }
  .tdot:nth-child(3) {
    animation-delay: 0.3s;
  }
  @keyframes typingBounce {
    0%,
    60%,
    100% {
      transform: translateY(0);
      opacity: 0.5;
    }
    30% {
      transform: translateY(-4px);
      opacity: 1;
    }
  }

  .chat-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0 14px 12px;
    flex-shrink: 0;
  }
  .chip {
    padding: 7px 12px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface);
    font-size: 12px;
    font-weight: 600;
    color: var(--ink);
    transition: background 0.15s ease;
  }
  .chip:hover:not(:disabled) {
    background: var(--chip);
  }
  .chip:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .chat-foot {
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }
  .staff-call {
    width: 100%;
    height: 44px;
    font-size: 13px;
  }
  .staff-call.called {
    background: var(--green-bg);
    border-color: transparent;
    color: var(--green);
    cursor: default;
  }
</style>
