let prices = null; // {dates, columns}

const $ = (id) => document.getElementById(id);
const dark = matchMedia("(prefers-color-scheme: dark)").matches;
const layoutBase = {
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: dark ? "#e6e9ef" : "#1c2330" },
  margin: { l: 50, r: 20, t: 30, b: 40 },
};

$("end").value = new Date().toISOString().slice(0, 10);

document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
    $("tickers-form").hidden = t.dataset.tab !== "tickers";
    $("csv-form").hidden = t.dataset.tab !== "csv";
  })
);

function setStatus(msg, isError = false, warnings = []) {
  const s = $("status");
  s.className = isError ? "error" : "";
  s.textContent = msg;
  warnings.forEach((w) => {
    const d = document.createElement("div");
    d.className = "warn";
    d.textContent = w;
    s.appendChild(d);
  });
}

async function api(path, options) {
  const r = await fetch(path, options);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = body.detail;
    throw new Error(typeof d === "string" ? d : r.status === 429 ? "Rate limit hit, try again shortly" : "Request failed");
  }
  return body;
}

// Show an indeterminate progress bar on a card while an async step runs.
async function tracked(barId, fn) {
  const bar = $(barId);
  const card = bar.closest(".card");
  const buttons = card.querySelectorAll("button");
  bar.hidden = false;
  card.setAttribute("aria-busy", "true");
  buttons.forEach((b) => (b.disabled = true));
  try {
    return await fn();
  } finally {
    bar.hidden = true;
    card.removeAttribute("aria-busy");
    buttons.forEach((b) => (b.disabled = false));
  }
}

const postJson = (path, data) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

async function loaded(data) {
  prices = { dates: data.dates, columns: data.columns };
  const names = Object.keys(prices.columns);
  setStatus(`Loaded ${names.length} tickers, ${prices.dates.length} rows.`, false, data.warnings);
  $("corr-card").hidden = false;
  let corr;
  try {
    corr = await tracked("prog-corr", () => postJson("/api/correlation", prices));
  } catch (e) {
    $("corr-card").hidden = true;
    throw e;
  }
  drawHeatmap(corr);
  for (const id of ["sel-y", "sel-x"]) {
    $(id).innerHTML = names.map((n) => `<option>${n}</option>`).join("");
  }
  $("sel-x").selectedIndex = 1;
  $("result-card").hidden = false;
}

function drawHeatmap(c) {
  Plotly.newPlot("heatmap", [{
    z: c.matrix, x: c.tickers, y: c.tickers, type: "heatmap",
    zmin: -1, zmax: 1, colorscale: "RdBu", reversescale: true,
    hovertemplate: "%{y} / %{x}: %{z:.2f}<extra></extra>",
  }], { ...layoutBase, height: 420, yaxis: { autorange: "reversed" } }, { responsive: true });
  $("heatmap").on("plotly_click", (e) => {
    const p = e.points[0];
    if (p.x === p.y) return;
    $("sel-y").value = p.y;
    $("sel-x").value = p.x;
    runTest();
  });
}

function stat(label, value, cls = "") {
  return `<div class="stat"><span>${label}</span><b class="${cls}">${value}</b></div>`;
}

async function runTest() {
  try {
    const r = await tracked("prog-coint", () => postJson("/api/cointegration", {
      prices, ticker_y: $("sel-y").value, ticker_x: $("sel-x").value,
      window: +$("window").value, rolling: $("rolling").checked,
    }));
    const ok = r.cointegrated_5pct;
    $("stats").innerHTML = [
      stat("Engle-Granger p-value", r.p_value.toFixed(4), ok ? "good" : "bad"),
      stat("Result (5%)", ok ? "Cointegrated" : "Not cointegrated", ok ? "good" : "bad"),
      stat("t-statistic", r.t_stat.toFixed(2)),
      stat("5% critical value", r.critical_values["5%"].toFixed(2)),
      stat("Hedge ratio (β)", r.beta.toFixed(4)),
      stat("Intercept (α)", r.alpha.toFixed(3)),
      stat("Spread ADF p-value", r.adf_p_value.toFixed(4)),
      stat("Half-life (days)", r.half_life ? r.half_life.toFixed(1) : "n/a"),
      stat("Observations", r.n_obs),
    ].join("");
    drawSpread(r);
    setStatus("");
  } catch (e) {
    setStatus(e.message, true);
  }
}

function drawSpread(r) {
  const vals = r.spread.filter((v) => v !== null);
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const sd = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length);
  const line = (y, name, dash) => ({ x: [r.dates[0], r.dates.at(-1)], y: [y, y], mode: "lines", name,
    line: { dash, width: 1, color: "#888" }, hoverinfo: "skip" });
  Plotly.newPlot("spread-plot", [
    { x: r.dates, y: r.spread, mode: "lines", name: "Spread", line: { width: 1.5 } },
    line(mean, "Mean", "solid"), line(mean + 2 * sd, "+2σ", "dash"), line(mean - 2 * sd, "−2σ", "dash"),
  ], { ...layoutBase, height: 320, title: `Spread: ${r.ticker_y} − β·${r.ticker_x} − α` }, { responsive: true });

  const zl = (y) => ({ x: [r.dates[0], r.dates.at(-1)], y: [y, y], mode: "lines", showlegend: false,
    line: { dash: "dash", width: 1, color: "#888" }, hoverinfo: "skip" });
  Plotly.newPlot("z-plot", [
    { x: r.dates, y: r.zscore, mode: "lines", name: "Z-score", line: { width: 1.5 } },
    zl(2), zl(-2), zl(0),
  ], { ...layoutBase, height: 260, title: "Z-score" }, { responsive: true });
}

$("tickers-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setStatus("Fetching prices…");
  try {
    const data = await tracked("prog-load", () => postJson("/api/prices/tickers", {
      tickers: $("tickers").value.split(","), start: $("start").value, end: $("end").value,
    }));
    await loaded(data);
  } catch (err) { setStatus(err.message, true); }
});

$("csv-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setStatus("Uploading…");
  const fd = new FormData();
  fd.append("file", $("csv").files[0]);
  try {
    const data = await tracked("prog-load", () => api("/api/prices/csv", { method: "POST", body: fd }));
    await loaded(data);
  } catch (err) { setStatus(err.message, true); }
});

$("run").addEventListener("click", runTest);
