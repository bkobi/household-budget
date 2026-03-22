/* ── State ── */
const MONTHS_HE = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                   "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"];

const state = {
  month: new Date().getMonth() + 1,
  year:  new Date().getFullYear(),
};

let donutChart = null;
let trendChart = null;

/* ── Toast ── */
function toast(msg, duration = 2800) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), duration);
}

/* ── Month navigation ── */
function updateMonthLabel() {
  document.getElementById("monthLabel").textContent =
    `${MONTHS_HE[state.month - 1]} ${state.year}`;
}

document.getElementById("prevMonth").addEventListener("click", () => {
  state.month--;
  if (state.month < 1) { state.month = 12; state.year--; }
  refreshAll();
});
document.getElementById("nextMonth").addEventListener("click", () => {
  state.month++;
  if (state.month > 12) { state.month = 1; state.year++; }
  refreshAll();
});

/* ── Tabs ── */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "stats") renderTrend();
  });
});

/* ── Overview ── */
async function renderOverview() {
  const [summary, alerts] = await Promise.all([
    API.getSummary(state.month, state.year),
    API.getAlerts(state.month, state.year),
  ]);

  // Metrics
  const remaining = summary.income - summary.total_spent;
  document.getElementById("metrics").innerHTML = `
    <div class="metric">
      <div class="metric-label">הכנסה חודשית</div>
      <div class="metric-value">₪${fmt(summary.income)}</div>
    </div>
    <div class="metric">
      <div class="metric-label">סה"כ הוצאות</div>
      <div class="metric-value danger">₪${fmt(summary.total_spent)}</div>
    </div>
    <div class="metric">
      <div class="metric-label">נשאר לחודש</div>
      <div class="metric-value ${remaining >= 0 ? "success" : "danger"}">₪${fmt(remaining)}</div>
    </div>
  `;

  // Alerts
  const alertsBox = document.getElementById("alertsBox");
  if (alerts.length) {
    alertsBox.style.display = "block";
    alertsBox.innerHTML = alerts.map(a => `
      <div class="alert-item ${a.level}">
        <span class="alert-icon">${a.level === "danger" ? "🔴" : "🟡"}</span>
        <span><strong>${catName(a.category)}</strong> — ${a.level === "danger" ? "חריגה" : "קרוב למגבלה"}: ₪${fmt(a.spent)} מתוך ₪${fmt(a.budget)} (${a.percent}%)</span>
      </div>
    `).join("");
  } else {
    alertsBox.style.display = "none";
  }

  // Donut chart
  const active = summary.categories.filter(c => c.spent > 0);
  if (donutChart) { donutChart.destroy(); donutChart = null; }
  if (active.length) {
    donutChart = new Chart(document.getElementById("donutChart"), {
      type: "doughnut",
      data: {
        labels: active.map(c => c.name),
        datasets: [{ data: active.map(c => c.spent), backgroundColor: active.map(c => c.color), borderWidth: 2 }],
      },
      options: {
        cutout: "65%",
        plugins: {
          legend: { position: "bottom", labels: { font: { size: 11 }, boxWidth: 12 } },
          tooltip: { callbacks: { label: ctx => ` ₪${fmt(ctx.parsed)}` } },
        },
      },
    });
  }

  // Budget bars
  document.getElementById("budgetBars").innerHTML = summary.categories
    .filter(c => c.spent > 0 || c.budget > 0)
    .map(c => {
      const pct = c.budget > 0 ? Math.min(100, (c.spent / c.budget) * 100) : 0;
      const barColor = pct >= 100 ? "#E24B4A" : pct >= 80 ? "#BA7517" : c.color;
      return `<div class="bar-row">
        <div class="bar-header">
          <span class="bar-cat">${c.icon} ${c.name}</span>
          <span class="bar-amounts">₪${fmt(c.spent)}${c.budget > 0 ? " / ₪" + fmt(c.budget) : ""}</span>
        </div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${barColor};"></div></div>
      </div>`;
    }).join("") || '<div class="empty">אין נתונים לחודש זה</div>';
}

/* ── Transactions ── */
async function renderTransactions() {
  const txns = await API.getTransactions(state.month, state.year);
  const list  = document.getElementById("txnList");

  if (!txns.length) {
    list.innerHTML = '<div class="empty">אין הוצאות לחודש זה</div>';
    return;
  }

  list.innerHTML = txns.map(t => {
    const cat = CATEGORIES.find(c => c.id === t.category) || CATEGORIES[CATEGORIES.length - 1];
    const d   = new Date(t.date);
    return `<div class="txn-item">
      <div class="txn-icon" style="background:${cat.color}22;">${cat.icon}</div>
      <div class="txn-info">
        <div class="txn-desc">${t.description}</div>
        <div class="txn-meta">${cat.name} · ${d.getDate()} ${MONTHS_HE[d.getMonth()]}</div>
      </div>
      <div class="txn-amount">-₪${fmt(t.amount)}</div>
      <button class="txn-del" data-id="${t.id}" title="מחק">✕</button>
    </div>`;
  }).join("");

  list.querySelectorAll(".txn-del").forEach(btn => {
    btn.addEventListener("click", async () => {
      await API.deleteTransaction(btn.dataset.id);
      toast("הוצאה נמחקה");
      refreshAll();
    });
  });
}

// Add transaction form
document.getElementById("addForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const desc   = document.getElementById("fDesc").value.trim();
  const amount = parseFloat(document.getElementById("fAmount").value);
  const cat    = document.getElementById("fCat").value;
  const date   = document.getElementById("fDate").value;

  try {
    await API.addTransaction({ description: desc, amount, category: cat, date });
    e.target.reset();
    document.getElementById("fDate").value = todayISO();
    toast("הוצאה נוספה ✓");
    refreshAll();
  } catch (err) {
    toast("שגיאה: " + err.message);
  }
});

/* ── Budget ── */
async function renderBudget() {
  const { budgets, income } = await API.getBudget(state.month, state.year);
  document.getElementById("incomeInput").value = income.amount || "";

  const budgetMap = Object.fromEntries(budgets.map(b => [b.category, b.amount]));

  document.getElementById("budgetSetup").innerHTML = CATEGORIES.map(cat => `
    <div class="budget-row-setup">
      <span class="budget-cat-name"><span style="font-size:1.1rem">${cat.icon}</span>${cat.name}</span>
      <input type="number" min="0" placeholder="₪ תקציב"
             value="${budgetMap[cat.id] ?? ""}"
             data-cat="${cat.id}"
             class="budget-input-field" />
      <button class="btn-primary" style="padding:.4rem .8rem;font-size:.8rem;" data-cat="${cat.id}">שמור</button>
    </div>
  `).join("");

  document.querySelectorAll("#budgetSetup button").forEach(btn => {
    btn.addEventListener("click", async () => {
      const catId  = btn.dataset.cat;
      const input  = document.querySelector(`.budget-input-field[data-cat="${catId}"]`);
      const amount = parseFloat(input.value) || 0;
      await API.setCategoryBudget({ month: state.month, year: state.year, category: catId, amount });
      toast("תקציב נשמר ✓");
      renderOverview();
    });
  });
}

async function saveIncome() {
  const amount = parseFloat(document.getElementById("incomeInput").value) || 0;
  await API.setIncome({ month: state.month, year: state.year, amount });
  toast("הכנסה נשמרה ✓");
  renderOverview();
}

/* ── Stats / Trend ── */
async function renderTrend() {
  const trend = await API.getTrend(state.year);
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  trendChart = new Chart(document.getElementById("trendChart"), {
    type: "bar",
    data: {
      labels: MONTHS_HE,
      datasets: [{
        label: "הוצאות (₪)",
        data: trend.map(t => t.total),
        backgroundColor: "#217346cc",
        borderColor: "#217346",
        borderWidth: 1,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ₪${fmt(ctx.parsed.y)}` } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => "₪" + fmt(v) } },
      },
    },
  });
}

/* ── Exports ── */
document.getElementById("btnExcel").addEventListener("click", () => {
  window.location.href = `/api/exports/excel?month=${state.month}&year=${state.year}`;
});
document.getElementById("btnPdf").addEventListener("click", () => {
  window.location.href = `/api/exports/pdf?month=${state.month}&year=${state.year}`;
});

/* ── Helpers ── */
function fmt(n) { return Math.round(n).toLocaleString("he-IL"); }
function todayISO() { return new Date().toISOString().slice(0, 10); }
function catName(id) {
  const c = CATEGORIES.find(c => c.id === id);
  return c ? c.name : id;
}

async function refreshAll() {
  updateMonthLabel();
  await Promise.all([renderOverview(), renderTransactions(), renderBudget()]);
}

// Init
document.getElementById("fDate").value = todayISO();
refreshAll();
