const tokenKey = "stalzone_access_token";
const state = new Map();
const sortState = new Map();
const appConfig = window.APP_CONFIG || {};

const authStatus = document.querySelector("#auth-status");
const loginForm = document.querySelector("#login-form");
const logoutButton = document.querySelector("#logout");

function token() {
  return localStorage.getItem(tokenKey);
}

function setAuthStatus() {
  const loggedIn = Boolean(token());
  authStatus.textContent = loggedIn
    ? "Токен сохранён. Доступны данные EU рынка."
    : "Войдите, чтобы получить данные рынка.";
  logoutButton.hidden = !loggedIn;
}

async function login(event) {
  event.preventDefault();
  const form = new FormData(loginForm);
  await authenticate(form.get("username"), form.get("password"));
  loginForm.reset();
}

async function authenticate(username, password) {
  const body = new URLSearchParams({ username, password });
  const response = await fetch("/auth/login", { method: "POST", body });
  if (!response.ok) {
    authStatus.textContent = `Не удалось войти: ${await errorText(response)}`;
    return false;
  }
  const data = await response.json();
  localStorage.setItem(tokenKey, data.access_token);
  setAuthStatus();
  return true;
}

async function request(endpoint, page = 1, params = {}) {
  if (!token()) throw new Error("Сначала выполните вход.");
  const query = new URLSearchParams({ ...params, page: String(page) });
  const response = await fetch(`${endpoint}?${query}`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json();
}

async function postJson(endpoint, body) {
  if (!token()) throw new Error("Сначала выполните вход.");
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { Authorization: `Bearer ${token()}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json();
}

async function errorText(response) {
  try {
    const data = await response.json();
    return data.detail || JSON.stringify(data);
  } catch {
    return response.statusText;
  }
}

function format(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value);
  return String(value);
}

function itemRows(items, top = false) {
  const columns = top
    ? ["Название", "Категория", "Цена выкупа", "Недельная медиана", "Скидка", "Объём 24ч", "Объём недели", "Оценка"]
    : ["Название", "Категория", "Цена выкупа", "Ставка", "Медиана 24ч", "VWAP", "Объём 24ч", "Лотов", "Обновлено"];
  const rows = items.map((item) => top
    ? [item.name, item.category, item.current_buyout_unit_price, item.weekly_median_unit_price, `${format(item.discount_percent)}%`, item.daily_trade_volume, item.weekly_trade_volume, item.buy_score]
    : [item.name, item.category, item.current_buyout_unit_price, item.current_bid_unit_price, item.median_unit_price, item.vwap_unit_price, item.trade_volume, item.lots_total, item.observed_at]);
  return table(columns, rows);
}

function opportunityRows(opportunities) {
  return table(
    ["Название", "Цена покупки", "Медиана сделок 24ч", "После комиссии 5%", "Прибыль/шт.", "Маржа", "Объём 24ч", "Лоты получены"],
    opportunities.map((item) => [
      item.name,
      item.buyout_unit_price,
      item.reference_sale_unit_price,
      item.expected_net_sale_unit_price,
      item.profit_per_unit,
      item.margin_percent === null ? null : `${format(item.margin_percent)}%`,
      item.trade_volume_24h,
      item.lots_observed_at,
    ]),
  );
}

function craftRows(crafts) {
  return table(
    ["Результат", "Станок", "Энергия", "Ингредиенты", "Стоимость", "Цена результата", "Прибыль", "Маржа"],
    crafts.map((craft) => {
      const profit = craft.profit || {};
      return [
        craft.results.map(component => `${component.name || component.item_id} ×${format(component.amount)}`).join(", "),
        craft.bench,
        craft.energy,
        craft.ingredients.map(component => `${component.name || component.item_id} ×${format(component.amount)} (${format(component.unit_price)})`).join("; "),
        profit.total_cost,
        profit.result_value,
        profit.profit,
        profit.margin_percent === undefined || profit.margin_percent === null ? null : `${format(profit.margin_percent)}%`,
      ];
    }),
  );
}

function table(columns, rows) {
  const head = columns.map(column => `<th>${escapeHtml(column)}</th>`).join("");
  const body = rows.map(row => `<tr>${row.map(value => `<td class="${typeof value === "number" ? "number" : ""}">${escapeHtml(format(value))}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

async function load(targetId, endpoint, params = {}, append = false) {
  const target = document.querySelector(`#${targetId}`);
  const previous = state.get(targetId);
  const page = append && previous ? previous.page + 1 : 1;
  target.innerHTML = append ? target.innerHTML : "<p class=\"muted\">Загрузка…</p>";
  try {
    const data = await request(endpoint, page, params);
    const entries = data.items || data.crafts || data.opportunities || [];
    const rendered = data.opportunities
      ? opportunityRows(entries)
      : data.items
        ? itemRows(entries, endpoint.endsWith("/top"))
        : craftRows(entries);
    target.innerHTML = append ? target.innerHTML.replace(/<button class="more"[\s\S]*?<\/button>/, "") + rendered : rendered;
    if (!entries.length && !append) target.innerHTML = "<p class=\"muted\">Нет данных. Для рейтингов нужны накопленные цены и история сделок.</p>";
    state.set(targetId, { endpoint, params, page, hasMore: entries.length === 20 });
    if (entries.length === 20) addMoreButton(targetId);
  } catch (error) {
    target.innerHTML = `<p class="error">Ошибка: ${escapeHtml(error.message)}</p>`;
  }
}

function addMoreButton(targetId) {
  const target = document.querySelector(`#${targetId}`);
  const button = document.querySelector("#more-template").content.firstElementChild.cloneNode(true);
  button.addEventListener("click", () => {
    const current = state.get(targetId);
    load(targetId, current.endpoint, current.params, true);
  });
  target.append(button);
}

document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".tab, .view").forEach(element => element.classList.remove("active"));
  button.classList.add("active");
  document.querySelector(`#${button.dataset.view}`).classList.add("active");
}));

document.querySelectorAll(".search-form").forEach((form) => form.addEventListener("submit", (event) => {
  event.preventDefault();
  load(form.dataset.target, form.dataset.endpoint, { name: new FormData(form).get("name") });
}));

document.querySelectorAll(".sort-controls").forEach((controls) => controls.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-sort]");
  if (!button) return;
  const previous = sortState.get(controls.dataset.target);
  const order = previous && previous.sort === button.dataset.sort && previous.order === "desc" ? "asc" : "desc";
  sortState.set(controls.dataset.target, { sort: button.dataset.sort, order });
  controls.querySelectorAll("button").forEach((item) => { item.textContent = item.textContent.replace(/[ ↑↓]$/, ""); });
  button.textContent += order === "desc" ? " ↓" : " ↑";
  load(controls.dataset.target, controls.dataset.endpoint, { sort: button.dataset.sort, order });
}));

function recordRows(records) {
  return table(
    ["Предмет", "Скрафчено", "Себестоимость/шт.", "Всего", "Источник", "Продано", "Остаток", "Выручка", "Прибыль"],
    records.map((record) => [
      record.item_name,
      record.quantity,
      record.unit_cost,
      record.total_cost,
      record.cost_source === "recipe" ? "рецепт" : "рынок",
      record.sold_quantity,
      record.remaining_quantity,
      record.net_revenue,
      record.realized_profit,
    ]),
  );
}

async function loadRecords() {
  const target = document.querySelector("#records-result");
  target.innerHTML = "<p class=\"muted\">Загрузка…</p>";
  try {
    const data = await request("/craft-records");
    target.innerHTML = data.records.length ? recordRows(data.records) : "<p class=\"muted\">Записей пока нет.</p>";
    const select = document.querySelector("#sale-record-id");
    select.innerHTML = data.records
      .filter((record) => record.remaining_quantity > 0)
      .map((record) => `<option value="${record.id}">#${record.id} — ${escapeHtml(record.item_name)} (${record.remaining_quantity} шт.)</option>`)
      .join("");
  } catch (error) {
    target.innerHTML = `<p class="error">Ошибка: ${escapeHtml(error.message)}</p>`;
  }
}

document.querySelector("#craft-record-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await postJson("/craft-records", { item_name: form.get("item_name"), quantity: Number(form.get("quantity")) });
    event.currentTarget.reset();
    await loadRecords();
  } catch (error) {
    document.querySelector("#records-result").innerHTML = `<p class="error">Ошибка: ${escapeHtml(error.message)}</p>`;
  }
});

document.querySelector("#craft-sale-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await postJson(`/craft-records/${form.get("record_id")}/sales`, {
      quantity: Number(form.get("quantity")),
      unit_price: form.get("unit_price"),
    });
    event.currentTarget.reset();
    await loadRecords();
  } catch (error) {
    document.querySelector("#records-result").innerHTML = `<p class="error">Ошибка: ${escapeHtml(error.message)}</p>`;
  }
});

document.querySelector("#record-item-name").addEventListener("input", async (event) => {
  const value = event.target.value.trim();
  if (!value || !token()) return;
  try {
    const data = await request("/craft-records/suggestions", 1, { query: value });
    document.querySelector("#record-suggestions").innerHTML = data.items
      .map((item) => `<option value="${escapeHtml(item)}"></option>`)
      .join("");
  } catch {
    // Suggestions are optional; errors must not interrupt entering a record.
  }
});

document.querySelector("#load-records").addEventListener("click", loadRecords);

loginForm.addEventListener("submit", login);
logoutButton.addEventListener("click", () => { localStorage.removeItem(tokenKey); setAuthStatus(); });
setAuthStatus();
if (appConfig.testAutoLogin) {
  authenticate(appConfig.testAdminUsername, appConfig.testAdminPassword);
}
