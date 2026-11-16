<script>
  import Mascot from '../lib/Mascot.svelte'
  import { app, startCheckout } from '../lib/state.svelte.js'
  import { money } from '../lib/data.js'
</script>

<div class="complete">
  <span class="mascot-stage"><Mascot mood="cheer" size={21} /></span>
  <h1 class="title">You're all set.</h1>
  <p class="subtitle">Your items have been confirmed.</p>
  <p class="total tnum">{money(app.lastTotal)}</p>
  <button class="btn-red again-btn" onclick={startCheckout}>Start a new checkout</button>
</div>

<style>
  .complete {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 32px;
    overflow-y: auto;
  }
  .mascot-stage {
    width: 152px;
    height: 152px;
    flex-shrink: 0;
    border-radius: 44px;
    background: var(--green-bg);
    display: grid;
    place-items: center;
    animation: popIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .title {
    margin-top: 20px;
    font-size: 42px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.6px;
    animation: fadeUp 0.4s ease 0.08s both;
  }
  .subtitle {
    margin-top: 14px;
    font-size: 18px;
    line-height: 1;
    color: var(--ink);
    animation: fadeUp 0.4s ease 0.16s both;
  }
  .total {
    margin-top: 18px;
    font-size: 30px;
    line-height: 1;
    font-weight: 700;
    animation: fadeUp 0.4s ease 0.24s both;
  }
  .again-btn {
    margin-top: 32px;
    width: 360px;
    max-width: 100%;
    height: 64px;
    flex-shrink: 0;
    font-size: 18px;
    animation: fadeUp 0.4s ease 0.32s both;
  }
</style>
