// Thin API client — all fetch calls live here
const API = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async del(path) {
    const res = await fetch(path, { method: "DELETE" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Transactions
  getTransactions: (month, year) =>
    API.get(`/api/transactions/?month=${month}&year=${year}`),
  addTransaction: (data) =>
    API.post("/api/transactions/", data),
  deleteTransaction: (id) =>
    API.del(`/api/transactions/${id}`),

  // Budget
  getBudget: (month, year) =>
    API.get(`/api/budget/?month=${month}&year=${year}`),
  setCategoryBudget: (data) =>
    API.post("/api/budget/category", data),
  setIncome: (data) =>
    API.post("/api/budget/income", data),
  getAlerts: (month, year) =>
    API.get(`/api/budget/alerts?month=${month}&year=${year}`),

  // Stats
  getSummary: (month, year) =>
    API.get(`/api/stats/summary?month=${month}&year=${year}`),
  getTrend: (year) =>
    API.get(`/api/stats/trend?year=${year}`),
};
