<script>
  import Icon from '../../lib/Icon.svelte'
  import ProductArt from '../../lib/ProductArt.svelte'
  import Modal from '../../lib/Modal.svelte'
  import PageHead from './PageHead.svelte'
  import { app, toast } from '../../lib/state.svelte.js'
  import { CATEGORIES } from '../../lib/data.js'

  let search = $state('')
  let category = $state('All categories')
  let status = $state('All statuses')
  let page = $state(0)
  let menuSku = $state(null)
  let addOpen = $state(false)
  let imagesSku = $state(null)
  let newName = $state('')
  let newCategory = $state(CATEGORIES[0])

  const thumbBg = { chip: 'var(--chip)', beige: 'var(--beige)', green: 'var(--green-bg)', amber: 'var(--amber-bg)' }
  const artFor = { Dairy: 'milk', 'Dairy alternatives': 'milk', Produce: 'apple', Drinks: 'water', Snacks: 'bar' }

  const readyCount = $derived(app.products.filter((p) => p.status === 'Ready').length)
  const needCount = $derived(app.products.filter((p) => p.status === 'Needs images').length)
  const categoryCount = $derived(new Set(app.products.map((p) => p.category)).size)
  const filtered = $derived(
    app.products.filter((p) => {
      const q = search.trim().toLowerCase()
      const matchQ = !q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)
      const matchC = category === 'All categories' || p.category === category
      const matchS = status === 'All statuses' || p.status === status
      return matchQ && matchC && matchS
    }),
  )
  const pages = $derived(Math.max(1, Math.ceil(filtered.length / 6)))
  const visible = $derived(filtered.slice(page * 6, page * 6 + 6))
  const imagesProduct = $derived(app.products.find((p) => p.sku === imagesSku) ?? null)

  const stats = $derived([
    {
      label: 'Products in catalog',
      value: app.products.length,
      delta: app.products.length
        ? `Across ${categoryCount} ${categoryCount === 1 ? 'category' : 'categories'}`
        : 'No products yet',
      tone: app.products.length ? 'green' : 'muted',
      icon: 'box',
    },
    {
      label: 'Ready to recognize',
      value: readyCount,
      delta: readyCount ? `Available at ${app.kioskName}` : 'Nothing ready yet',
      tone: readyCount ? 'green' : 'muted',
      icon: 'checkCircle',
    },
    {
      label: 'Need more images',
      value: needCount,
      delta: needCount ? 'Add photos before retraining' : 'All caught up',
      tone: needCount ? 'amber' : 'muted',
      icon: 'image',
    },
  ])

  $effect(() => {
    if (page >= pages) page = pages - 1
  })
  $effect(() => {
    if (app.catalogImagesRequest > 0) {
      app.catalogImagesRequest = 0
      openImages(null)
    }
  })

  function clearFilters() {
    search = ''
    category = 'All categories'
    status = 'All statuses'
  }

  function addProduct() {
    const name = newName.trim()
    if (!name) return
    const num = app.products.length + 1
    app.products.push({
      sku: `PRD-${String(num).padStart(3, '0')}`,
      name,
      category: newCategory,
      photos: 0,
      status: 'Needs images',
      art: artFor[newCategory],
      thumb: 'amber',
      price: 0,
    })
    newName = ''
    addOpen = false
    toast(`Added “${name}” to the catalog.`)
  }

  function deleteProduct(sku) {
    const idx = app.products.findIndex((p) => p.sku === sku)
    if (idx === -1) return
    const [removed] = app.products.splice(idx, 1)
    menuSku = null
    toast(`Removed “${removed.name}”.`, {
      label: 'Undo',
      run: () => app.products.splice(idx, 0, removed),
    })
  }

  function addPhotos() {
    if (!imagesProduct) return
    imagesProduct.photos += 12
    if (imagesProduct.photos >= 20 && imagesProduct.status === 'Needs images') {
      imagesProduct.status = 'Ready'
    }
  }

  function openImages(sku) {
    imagesSku = sku ?? app.products.find((p) => p.status === 'Needs images')?.sku ?? app.products[0]?.sku ?? null
    menuSku = null
  }
</script>

<div class="page">
  <PageHead title="Product catalog" subtitle="Keep the items your kiosk knows up to date.">
    <button class="btn-red head-btn" onclick={() => (addOpen = true)}>Add product</button>
  </PageHead>

  <div class="stats">
    {#each stats as s}
      <div class="card stat">
        <span class="stat-label">{s.label}</span>
        <span class="stat-value tnum">{s.value}</span>
        <span class="stat-delta {s.tone}">{s.delta}</span>
        <span class="icon-chip stat-icon"><Icon name={s.icon} size={14} /></span>
      </div>
    {/each}
  </div>

  <div class="card table-card">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="search-wrap">
        <input class="field search" type="text" placeholder="Search products…" bind:value={search} aria-label="Search products" />
        <span class="search-icon"><Icon name="search" size={13} /></span>
      </div>
      <div class="select-wrap cat-select">
        <select class="field select" bind:value={category} aria-label="Filter by category">
          <option>All categories</option>
          {#each CATEGORIES as c}<option>{c}</option>{/each}
        </select>
        <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
      </div>
      <div class="select-wrap status-select">
        <select class="field select" bind:value={status} aria-label="Filter by status">
          <option>All statuses</option>
          <option>Ready</option>
          <option>Needs images</option>
        </select>
        <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
      </div>
      <button class="btn-line manage-btn" onclick={() => openImages(null)}>Manage images</button>
    </div>

    <!-- Table -->
    <div class="table">
      <div class="trow thead">
        <span class="th">Product</span>
        <span class="th">SKU</span>
        <span class="th col-cat">Category</span>
        <span class="th col-img">Images</span>
        <span class="th">Status</span>
        <span class="th"></span>
      </div>

      {#each visible as p}
        <div class="trow">
          <span class="product-cell">
            <span class="thumb" style="background: {thumbBg[p.thumb]}">
              <ProductArt kind={p.art} size={22} />
            </span>
            <span class="name">{p.name}</span>
          </span>
          <span class="cell tnum">{p.sku}</span>
          <span class="cell col-cat">{p.category}</span>
          <span class="cell col-img tnum">{p.photos} photos</span>
          <span class="pill row-badge {p.status === 'Ready' ? 'pill-green' : 'pill-amber'}">{p.status}</span>
          <span class="actions-cell">
            <button
              class="dots"
              onclick={() => (menuSku = menuSku === p.sku ? null : p.sku)}
              aria-label="More actions for {p.name}"
            >
              •••
            </button>
            {#if menuSku === p.sku}
              <div class="row-menu" role="menu">
                <button class="menu-item" role="menuitem" onclick={() => openImages(p.sku)}>
                  <Icon name="image" size={14} /> Manage images
                </button>
                <button class="menu-item danger" role="menuitem" onclick={() => deleteProduct(p.sku)}>
                  <Icon name="x" size={14} /> Delete product
                </button>
              </div>
            {/if}
          </span>
        </div>
      {/each}
    </div>

    {#if menuSku}
      <div class="menu-catcher" onclick={() => (menuSku = null)} role="presentation"></div>
    {/if}

    {#if app.products.length === 0}
      <div class="empty-state table-empty">
        <span class="icon-chip"><Icon name="box" size={18} /></span>
        <p class="empty-title">No products yet.</p>
        <p class="empty-sub">Add your first product so the kiosk can start recognizing items.</p>
        <button class="btn-red empty-btn" onclick={() => (addOpen = true)}>Add product</button>
      </div>
    {:else if filtered.length === 0}
      <div class="empty-state table-empty">
        <span class="icon-chip"><Icon name="search" size={18} /></span>
        <p class="empty-title">No products match your filters.</p>
        <p class="empty-sub">Try a different search, or clear the filters to see everything.</p>
        <button class="btn-line empty-btn" onclick={clearFilters}>Clear filters</button>
      </div>
    {/if}

    <div class="table-footer">
      <span class="footer-count tnum">Showing {visible.length} of {filtered.length} products</span>
      {#if filtered.length > 6}
        <button class="next-btn" onclick={() => (page = (page + 1) % pages)}>Next products</button>
      {/if}
    </div>
  </div>
</div>

{#if addOpen}
  <Modal title="Add product" onclose={() => (addOpen = false)}>
    {#snippet footer()}
      <button class="btn-line modal-btn" onclick={() => (addOpen = false)}>Cancel</button>
      <button class="btn-red modal-btn" disabled={!newName.trim()} onclick={addProduct}>Add product</button>
    {/snippet}
    <label class="form-label" for="np-name">Product name</label>
    <input id="np-name" class="field form-input" type="text" placeholder="e.g. Sparkling water 500 mL" bind:value={newName} />
    <label class="form-label" for="np-cat">Category</label>
    <div class="select-wrap form-select">
      <select id="np-cat" class="field select" bind:value={newCategory}>
        {#each CATEGORIES as c}<option>{c}</option>{/each}
      </select>
      <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
    </div>
    <p class="form-note">New products start as “Needs images” until you add training photos.</p>
  </Modal>
{/if}

{#if imagesProduct}
  <Modal title="Manage images" onclose={() => (imagesSku = null)}>
    {#snippet footer()}
      <button class="btn-line modal-btn" onclick={() => (imagesSku = null)}>Done</button>
      <button class="btn-red modal-btn" onclick={addPhotos}>
        <Icon name="upload" size={15} /> Add 12 photos
      </button>
    {/snippet}
    <label class="form-label" for="img-prod">Product</label>
    <div class="select-wrap form-select">
      <select id="img-prod" class="field select" bind:value={imagesSku}>
        {#each app.products as p}<option value={p.sku}>{p.name}</option>{/each}
      </select>
      <span class="select-chev"><Icon name="chevronDown" size={15} /></span>
    </div>
    <div class="img-status">
      <span class="img-thumb" style="background: {thumbBg[imagesProduct.thumb]}">
        <ProductArt kind={imagesProduct.art} size={26} />
      </span>
      <div>
        <p class="img-count">{imagesProduct.photos} photos</p>
        <p class="img-note">
          {imagesProduct.status === 'Ready' ? 'Ready to recognize.' : 'Add at least 20 photos to make this product ready.'}
        </p>
      </div>
      <span class="pill {imagesProduct.status === 'Ready' ? 'pill-green' : 'pill-amber'} img-badge">{imagesProduct.status}</span>
    </div>
  </Modal>
{/if}

<style>
  .page {
    animation: fadeIn 0.25s ease both;
  }
  .head-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 12px;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 28px;
  }
  .stat {
    position: relative;
    height: 128px;
  }
  .stat-label {
    position: absolute;
    left: 25px;
    top: 17px;
    font-size: 13px;
    line-height: 1;
    color: var(--muted);
  }
  .stat-value {
    position: absolute;
    left: 25px;
    top: 49px;
    font-size: 24px;
    line-height: 1;
    font-weight: 700;
    letter-spacing: -0.3px;
  }
  .stat-delta {
    position: absolute;
    left: 25px;
    top: 95px;
    font-size: 12px;
    line-height: 1;
    font-weight: 600;
    max-width: calc(100% - 50px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stat-delta.green {
    color: var(--green);
  }
  .stat-delta.amber {
    color: var(--amber);
  }
  .stat-delta.muted {
    color: var(--muted);
    font-weight: 500;
  }
  .stat-icon {
    position: absolute;
    right: 20px;
    top: 16px;
  }

  .table-card {
    position: relative;
    min-height: 536px;
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    padding: 24px;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
  .search-wrap {
    position: relative;
    flex: 1;
    min-width: 200px;
    height: 44px;
  }
  .search {
    width: 100%;
    height: 100%;
    padding-right: 40px;
    font-weight: 400;
  }
  .search-icon {
    position: absolute;
    right: 14px;
    top: 16px;
    display: flex;
    color: var(--muted);
    pointer-events: none;
  }
  .select-wrap {
    position: relative;
    height: 44px;
  }
  .cat-select {
    width: 178px;
  }
  .status-select {
    width: 190px;
  }
  .select {
    width: 100%;
    height: 100%;
    appearance: none;
    padding-right: 36px;
    cursor: pointer;
  }
  .select-chev {
    position: absolute;
    right: 12px;
    top: 15px;
    display: flex;
    color: var(--muted);
    pointer-events: none;
  }
  .manage-btn {
    height: 40px;
    padding: 0 20px;
    font-size: 13px;
    white-space: nowrap;
  }

  .table {
    margin-top: 24px;
  }
  .trow {
    position: relative;
    display: grid;
    grid-template-columns: minmax(180px, 2.4fr) 1fr 1fr 0.8fr 130px 40px;
    align-items: center;
    gap: 12px;
    height: 56px;
  }
  .trow + .trow {
    border-top: 1px solid var(--border);
  }
  .thead {
    height: 38px;
    border-bottom: 1px solid var(--border);
  }
  .th {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .product-cell {
    display: flex;
    align-items: center;
    gap: 17px;
    min-width: 0;
  }
  .thumb {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    border-radius: 8px;
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .name {
    font-size: 14px;
    line-height: 1.2;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cell {
    font-size: 12px;
    line-height: 1;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row-badge {
    width: 112px;
    height: 26px;
    font-size: 12px;
  }
  .actions-cell {
    position: relative;
    display: flex;
    justify-content: flex-end;
  }
  .dots {
    font-size: 14px;
    line-height: 1;
    letter-spacing: 1px;
    color: var(--muted);
    padding: 2px 4px;
    border-radius: 6px;
  }
  .dots:hover {
    color: var(--ink);
    background: var(--chip);
  }

  .menu-catcher {
    position: fixed;
    inset: 0;
    z-index: 15;
  }
  .row-menu {
    position: absolute;
    right: 0;
    top: 30px;
    width: 184px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 4px;
    z-index: 20;
    box-shadow: 0 8px 22px rgba(23, 23, 23, 0.18);
    animation: popIn 0.12s ease both;
  }
  .menu-item {
    display: flex;
    align-items: center;
    gap: 9px;
    width: 100%;
    padding: 9px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    color: var(--ink);
    text-align: left;
  }
  .menu-item:hover {
    background: var(--chip);
  }
  .menu-item.danger {
    color: var(--red);
  }

  .table-empty {
    flex: 1;
    padding: 40px 24px;
  }
  .empty-btn {
    margin-top: 18px;
    height: 42px;
    padding: 0 22px;
    font-size: 13px;
  }
  .table-footer {
    margin-top: auto;
    padding-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .footer-count {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .next-btn {
    font-size: 11px;
    line-height: 1;
    color: var(--muted);
  }
  .next-btn:hover {
    color: var(--ink);
    text-decoration: underline;
  }

  .form-label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .form-input {
    width: 100%;
    font-weight: 400;
    margin-bottom: 18px;
  }
  .form-select {
    width: 100%;
    margin-bottom: 16px;
  }
  .form-note {
    font-size: 12px;
    line-height: 1.5;
    color: var(--muted);
  }
  .modal-btn {
    height: 42px;
    padding: 0 20px;
    font-size: 13px;
  }
  .img-status {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px;
    background: var(--bg);
    border-radius: 10px;
  }
  .img-thumb {
    width: 48px;
    height: 48px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink);
    flex-shrink: 0;
  }
  .img-count {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 4px;
  }
  .img-note {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.4;
  }
  .img-badge {
    margin-left: auto;
    height: 26px;
    padding: 0 12px;
    font-size: 12px;
    flex-shrink: 0;
  }

  @media (max-width: 1000px) {
    .stats {
      grid-template-columns: 1fr;
    }
    .trow {
      grid-template-columns: minmax(140px, 2fr) 1fr 120px 40px;
    }
    .col-cat,
    .col-img {
      display: none;
    }
  }
  @media (max-width: 640px) {
    .search-wrap {
      min-width: 160px;
    }
    .trow {
      grid-template-columns: minmax(0, 1fr) 104px 36px;
      gap: 8px;
    }
    .trow > :nth-child(2) {
      display: none;
    }
  }
</style>
