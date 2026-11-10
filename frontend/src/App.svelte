<main>
  <header>
    <p class="eyebrow">Self-checkout</p>
    <h1>Auto Vision Checkout</h1>
  </header>

  <div class="checkout">
    <section class="camera" aria-label="Camera preview">
      <p>Camera preview</p>
    </section>

    <section class="basket" aria-labelledby="basket-heading">
      <h2 id="basket-heading">Your items</h2>
      <p>Your basket is empty.</p>
      <div class="total">
        <span>Total</span>
        <strong>$0.00</strong>
      </div>
    </section>
  </div>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: #f2f3f5;
    color: #20242a;
    font-family: system-ui, sans-serif;
  }

  main {
    width: min(calc(100% - 2rem), 74rem);
    margin-inline: auto;
    padding-block: clamp(1.5rem, 5vw, 4rem);
  }

  h1,
  h2,
  p {
    margin: 0;
  }

  h1 {
    margin-block: 0.4rem;
    font-size: clamp(1.75rem, 5vw, 3rem);
  }

  .eyebrow {
    font-size: 0.875rem;
    font-weight: 650;
  }

  .checkout {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1rem;
    margin-top: 1.75rem;
  }

  .camera,
  .basket {
    border-radius: 0.75rem;
    padding: 1.25rem;
  }

  .camera {
    display: grid;
    min-height: clamp(14rem, 43vw, 28rem);
    place-items: center;
    background: #242931;
    color: #f2f3f5;
  }

  .basket {
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: 1rem;
    background: #fff;
  }

  .total {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    border-top: 1px solid #d9dde3;
    padding-top: 1rem;
  }

  @media (max-width: 40rem) {
    .checkout {
      grid-template-columns: 1fr;
    }
  }
</style>
