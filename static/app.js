let catalog = [];
let basket = [];

const money = value => new Intl.NumberFormat('es-ES', {style: 'currency', currency: 'EUR'}).format(value);
const byId = id => catalog.find(product => product.id === id);

function optionText(product) {
  const bits = [product.name, product.brand, product.store, product.weight_g ? `${product.weight_g} g` : 'sin formato'];
  return bits.filter(Boolean).join(' · ');
}

function renderBasket() {
  const root = document.querySelector('#basket');
  root.innerHTML = '';
  root.classList.toggle('empty', basket.length === 0);
  if (!basket.length) {
    root.textContent = 'Añade productos al carrito.';
    return;
  }
  basket.forEach((item, index) => {
    const product = byId(item.product_id);
    const row = document.querySelector('#basket-item-template').content.firstElementChild.cloneNode(true);
    row.querySelector('span').textContent = product.name;
    const qty = row.querySelector('input');
    qty.value = item.quantity;
    qty.addEventListener('change', () => { basket[index].quantity = Number(qty.value) || 1; });
    row.querySelector('.remove').addEventListener('click', () => { basket.splice(index, 1); renderBasket(); });
    root.append(row);
  });
}

function renderResult(payload) {
  const root = document.querySelector('#result');
  root.innerHTML = '';
  root.classList.remove('empty');
  if (!payload.plan) {
    root.textContent = payload.message;
    return;
  }
  const summary = document.createElement('div');
  summary.className = 'summary';
  summary.innerHTML = `<div><small>Total productos</small><strong>${money(payload.plan.product_cost)}</strong></div><div><small>Coste adicional</small><strong>${money(payload.plan.travel_cost)}</strong></div><div><small>Total recomendado</small><strong>${money(payload.plan.total)}</strong></div>`;
  root.append(summary);
  Object.entries(payload.plan.stores).forEach(([store, lines]) => {
    const group = document.createElement('section');
    group.className = 'store-group';
    group.innerHTML = `<h3>${store}</h3>`;
    lines.forEach(line => {
      const note = line.score === 1 ? 'exacto' : `${line.reason} · confianza ${Math.round(line.score * 100)}%`;
      const div = document.createElement('div');
      div.className = 'line';
      div.innerHTML = `<span>${line.name}<small>${line.quantity} × ${money(line.price_eur)} · ${note}</small></span><strong>${money(line.line_total)}</strong>`;
      group.append(div);
    });
    root.append(group);
  });
  if (payload.unavailable.length) {
    const missing = document.createElement('p');
    missing.className = 'warning';
    missing.textContent = `Sin precio: ${payload.unavailable.join(', ')}`;
    root.append(missing);
  }
  const message = document.createElement('p');
  message.className = 'muted';
  message.textContent = payload.message;
  root.append(message);
}

async function optimize() {
  if (!basket.length) return;
  const response = await fetch('/api/plan', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    items: basket,
    allow_equivalents: document.querySelector('#equivalents').checked,
    include_loyalty: document.querySelector('#loyalty').checked,
    max_stores: document.querySelector('#max-stores').value,
    extra_store_cost: document.querySelector('#extra-cost').value,
  })});
  renderResult(await response.json());
}

function fillSelect(select) {
  catalog.forEach(product => {
    const option = document.createElement('option');
    option.value = product.id;
    option.textContent = optionText(product);
    select.append(option);
  });
}

async function load() {
  const [catalogResponse, qualityResponse] = await Promise.all([fetch('/api/catalog'), fetch('/api/quality')]);
  catalog = await catalogResponse.json();
  const quality = await qualityResponse.json();
  fillSelect(document.querySelector('#product-select'));
  fillSelect(document.querySelector('#obs-product'));
  document.querySelector('#quality').textContent = `${quality.products} productos · ${quality.observations} precios históricos · ${quality.semantic_flags.length} avisos de calidad`;
  document.querySelector('#obs-date').value = new Date().toISOString().slice(0, 10);
}

document.querySelector('#add-item').addEventListener('click', () => {
  const product_id = document.querySelector('#product-select').value;
  const quantity = Number(document.querySelector('#quantity').value) || 1;
  const existing = basket.find(item => item.product_id === product_id);
  if (existing) existing.quantity += quantity;
  else basket.push({product_id, quantity});
  renderBasket();
});
document.querySelector('#optimize').addEventListener('click', optimize);
document.querySelector('#observation-form').addEventListener('submit', async event => {
  event.preventDefault();
  const response = await fetch('/api/observations', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    product_id: document.querySelector('#obs-product').value,
    store: document.querySelector('#obs-store').value,
    price_eur: document.querySelector('#obs-price').value,
    promotion_eur: document.querySelector('#obs-promo').value,
    observed_on: document.querySelector('#obs-date').value,
    loyalty_required: document.querySelector('#obs-loyalty').checked,
  })});
  const payload = await response.json();
  const status = document.querySelector('#observation-status');
  status.textContent = payload.saved ? 'Precio guardado. Vuelve a optimizar la cesta.' : payload.error;
  if (payload.saved) event.target.reset();
});

load();
