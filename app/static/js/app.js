const $ = (selector) => document.querySelector(selector);
const form = $("#trade-form");
const searchInput = $("#instrument-search");
const instrumentSelect = $("#instrument");
const message = $("#form-message");
const FAVORITES_KEY = "piplot.favorites";
const HISTORY_KEY = "piplot.history";
let instruments = [];
let activeCategory = "All";
let latestResult = null;
let requestVersion = 0;
let debounceTimer;

const readStored = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
};
const favorites = () => readStored(FAVORITES_KEY, []);
const selectedDirection = () => $('input[name="direction"]:checked').value;
const selectedTpMethod = () => $('input[name="tp_method"]:checked').value;
const instrument = () => instruments.find((item) => item.symbol === instrumentSelect.value);
const numberValue = (selector) => Number($(selector).value);
const currency = (value) => Number.isFinite(value)
  ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value)
  : "—";

function renderCategories() {
  const categories = ["All", "Forex", "Crypto", "Metals", "Indices", "Energies", "Favourites"];
  const counts = Object.fromEntries(categories.map((category) => [
    category,
    category === "All" ? instruments.length
      : category === "Favourites" ? instruments.filter((item) => favorites().includes(item.symbol)).length
        : instruments.filter((item) => item.category === category).length,
  ]));
  $("#category-pills").innerHTML = categories.map((category) =>
    `<button type="button" class="category-pill${category === activeCategory ? " active" : ""}" data-category="${category}">${category} ${counts[category]}</button>`
  ).join("");
  $("#category-pills").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      activeCategory = button.dataset.category;
      renderCategories();
      renderInstruments();
    });
  });
}

function renderInstruments() {
  const term = searchInput.value.trim().toLowerCase();
  const matching = instruments.filter((item) => {
    const categoryMatches = activeCategory === "All"
      || (activeCategory === "Favourites" ? favorites().includes(item.symbol) : item.category === activeCategory);
    return categoryMatches && `${item.symbol} ${item.name}`.toLowerCase().includes(term);
  });
  const current = instrumentSelect.value;
  instrumentSelect.innerHTML = matching.length
    ? matching.map((item) => `<option value="${item.symbol}">${item.symbol} — ${item.name}${item.calculation_status === "unavailable" ? " · no profile" : ""}</option>`).join("")
    : '<option value="">No matching instruments</option>';
  if (matching.some((item) => item.symbol === current)) instrumentSelect.value = current;
  updateInstrumentMeta();
}

function updateInstrumentMeta() {
  const item = instrument();
  $("#instrument-category").textContent = item?.category || "—";
  const isAvailable = item?.calculation_status === "reference_estimate";
  $("#profile-label").textContent = isAvailable
    ? "Generic reference estimate · USD account"
    : "Calculation profile unavailable";
  const badge = document.querySelector(".estimate-badge");
  badge.classList.toggle("unavailable", !isAvailable);
  badge.innerHTML = `<span></span>${isAvailable ? "REFERENCE" : "UNAVAILABLE"}`;
  const isFavorite = item && favorites().includes(item.symbol);
  $("#favorite-button").classList.toggle("favorited", Boolean(isFavorite));
  $("#favorite-button").textContent = isFavorite ? "★" : "☆";
  $("#favorite-button").setAttribute("aria-label", isFavorite ? "Remove instrument from favourites" : "Add instrument to favourites");
}

function payload() {
  const rr = $("#rr").value === "custom" ? $("#custom-rr").value : $("#rr").value;
  const data = {
    symbol: instrumentSelect.value,
    direction: selectedDirection(),
    balance: $("#balance").value,
    risk_value: $("#risk-value").value,
    risk_mode: $("#risk-mode").value,
    entry: $("#entry").value,
    stop_loss: $("#stop-loss").value,
    tp_method: selectedTpMethod(),
  };
  if (data.tp_method === "rr") data.rr = rr;
  else data.take_profit = $("#take-profit").value;
  return data;
}

function clearResults() {
  latestResult = null;
  $("#copy-button").disabled = true;
  $("#result-volume").innerHTML = "— <small>lots</small>";
  ["result-instrument", "result-planned-risk", "result-risk-percent", "result-actual-risk",
    "result-actual-percent", "result-tp", "result-rr", "result-profit", "result-loss",
    "result-stop-distance", "result-target-distance"].forEach((id) => {
    const node = document.getElementById(id);
    node.textContent = id === "result-instrument" ? "Select a supported instrument to begin" : "—";
  });
  $("#result-warning").hidden = true;
  $("#learning-copy").hidden = true;
}

function displayResult(result) {
  latestResult = result;
  $("#copy-button").disabled = false;
  $("#result-volume").innerHTML = `${result.volume.toFixed(2)} <small>lots</small>`;
  $("#result-instrument").textContent = `${result.symbol} · ${result.direction}`;
  $("#result-planned-risk").textContent = currency(result.planned_risk);
  $("#result-risk-percent").textContent = `${result.risk_percent.toFixed(2)}% of balance`;
  $("#result-actual-risk").textContent = currency(result.actual_risk);
  $("#result-actual-percent").textContent = `${result.actual_risk_percent.toFixed(2)}% after rounding`;
  $("#result-tp").textContent = result.take_profit.toFixed(result.price_precision);
  $("#result-rr").textContent = `R:R 1 : ${result.rr.toFixed(2)}`;
  $("#result-profit").textContent = currency(result.gross_profit);
  $("#result-loss").textContent = currency(result.gross_loss);
  $("#result-stop-distance").textContent = result.stop_distance.toFixed(result.price_precision);
  $("#result-target-distance").textContent = result.target_distance.toFixed(result.price_precision);
  $("#profile-disclosure").textContent = result.profile_disclosure;
  const warning = $("#result-warning");
  warning.hidden = result.warnings.length === 0;
  warning.textContent = result.warnings.join(" ");
  $("#learning-copy").textContent = result.learning;
  $("#learning-copy").hidden = !$("#learn-button").getAttribute("aria-expanded") || $("#learn-button").getAttribute("aria-expanded") === "false";
  saveHistory(result);
}

async function calculate(showError = true) {
  const version = ++requestVersion;
  const item = instrument();
  updateRiskEquivalent();
  if (!item || item.calculation_status !== "reference_estimate") {
    clearResults();
    message.textContent = item
      ? `${item.symbol}: ${item.source_note}`
      : "Choose an instrument to calculate.";
    return;
  }
  try {
    const response = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const result = await response.json();
    if (version !== requestVersion) return;
    if (!response.ok) throw new Error(result.error || "Calculation could not be completed.");
    message.textContent = "";
    message.classList.remove("success");
    displayResult(result);
  } catch (error) {
    if (version !== requestVersion) return;
    clearResults();
    if (showError) message.textContent = error.message || "Unable to calculate. Check your inputs and try again.";
  }
}

function scheduleCalculate() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => calculate(), 100);
}

function updateRiskEquivalent() {
  const balance = numberValue("#balance");
  const amount = numberValue("#risk-value");
  if (!(balance > 0) || !(amount > 0)) {
    $("#risk-equivalent").textContent = "Enter a positive balance and risk amount.";
    return;
  }
  if ($("#risk-mode").value === "percent") {
    $("#risk-equivalent").textContent = `${amount}% risk = ${currency(balance * amount / 100)}`;
  } else {
    $("#risk-equivalent").textContent = `${currency(amount)} fixed risk = ${(amount / balance * 100).toFixed(2)}% of balance`;
  }
}

function saveHistory(result) {
  const history = readStored(HISTORY_KEY, []);
  const item = {
    symbol: result.symbol, direction: result.direction, volume: result.volume,
    risk: result.actual_risk, tp: result.take_profit, rr: result.rr, timestamp: Date.now(),
  };
  if (history[0]?.symbol === item.symbol && history[0]?.timestamp > Date.now() - 1500) return;
  history.unshift(item);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 5)));
  renderHistory();
}

function renderHistory() {
  const history = readStored(HISTORY_KEY, []);
  $("#history-list").innerHTML = history.map((item) =>
    `<div class="history-item"><strong>${item.symbol} ${item.direction}</strong> · ${item.volume.toFixed(2)} lots<br>Risk ${currency(item.risk)} · R:R 1:${item.rr.toFixed(2)}</div>`
  ).join("");
}

function resetForm() {
  form.reset();
  $("#balance").value = "10000";
  $("#risk-value").value = "1";
  $("#entry").value = "1.08500";
  $("#stop-loss").value = "1.08000";
  $("#rr").value = "2";
  $("#custom-rr").value = "2";
  $("#instrument-search").value = "";
  activeCategory = "All";
  renderCategories();
  renderInstruments();
  updateTpControls();
  document.querySelectorAll(".direction-option").forEach((option) => option.classList.toggle("selected", option.querySelector("input").checked));
  message.textContent = "";
  calculate();
}

function updateTpControls() {
  const isPrice = selectedTpMethod() === "price";
  $("#rr-controls").hidden = isPrice;
  $("#price-controls").hidden = !isPrice;
  $("#custom-rr").hidden = $("#rr").value !== "custom";
}

async function initialize() {
  try {
    const response = await fetch("/api/instruments");
    if (!response.ok) throw new Error("Instrument catalogue could not be loaded.");
    const data = await response.json();
    instruments = data.instruments;
    $("#instrument-count").textContent = `${instruments.length} instruments`;
    renderCategories();
    renderInstruments();
    instrumentSelect.value = "EURUSD";
    updateInstrumentMeta();
    renderHistory();
    updateRiskEquivalent();
    await calculate();
  } catch (error) {
    message.textContent = error.message;
  }
}

searchInput.addEventListener("input", renderInstruments);
instrumentSelect.addEventListener("change", () => { updateInstrumentMeta(); calculate(); });
$("#favorite-button").addEventListener("click", () => {
  const item = instrument();
  if (!item) return;
  const current = favorites();
  const next = current.includes(item.symbol) ? current.filter((symbol) => symbol !== item.symbol) : [...current, item.symbol];
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
  renderCategories();
  updateInstrumentMeta();
});
form.addEventListener("input", (event) => {
  if (event.target.name === "direction") {
    document.querySelectorAll(".direction-option").forEach((option) => option.classList.toggle("selected", option.querySelector("input").checked));
  }
  if (event.target.name === "tp_method") updateTpControls();
  if (event.target.id === "rr") $("#custom-rr").hidden = event.target.value !== "custom";
  scheduleCalculate();
});
form.addEventListener("change", (event) => {
  if (event.target.name === "tp_method") updateTpControls();
  scheduleCalculate();
});
form.addEventListener("submit", (event) => {
  event.preventDefault();
  calculate(true);
});
$("#reset-button").addEventListener("click", resetForm);
$("#clear-history").addEventListener("click", () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  message.textContent = "Recent plans cleared from this browser.";
  message.classList.add("success");
});
$("#copy-button").addEventListener("click", async () => {
  if (!latestResult) return;
  const result = latestResult;
  const summary = `${result.symbol} ${result.direction} | Entry ${result.entry} | SL ${result.stop_loss} | TP ${result.take_profit.toFixed(result.price_precision)} | ${result.volume.toFixed(2)} lots | Risk ${currency(result.actual_risk)} | R:R 1:${result.rr.toFixed(2)}`;
  try {
    await navigator.clipboard.writeText(summary);
    message.textContent = "Trade plan copied to clipboard.";
    message.classList.add("success");
  } catch {
    message.textContent = "Clipboard access was denied by your browser.";
    message.classList.remove("success");
  }
});
$("#learn-button").addEventListener("click", () => {
  const button = $("#learn-button");
  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", String(!expanded));
  button.querySelector("span").textContent = expanded ? "＋" : "−";
  $("#learning-copy").hidden = expanded || !latestResult;
});

initialize();
