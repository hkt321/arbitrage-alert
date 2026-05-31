(function (app) {
  const funds = app.mockFunds;
  const { getExecution } = app.executionRules;
  const { renderFundRows, getExecutionSummary } = app.tableView;

  const state = {
    category: "全部",
    sortKey: "premiumPct",
    sortDir: "desc",
    search: "",
    premiumThreshold: 3,
    turnoverThreshold: 0.5,
    desiredPurchaseYuan: 10000
  };

  const table = document.querySelector("#fundTable");
  const updatedAt = document.querySelector("#updatedAt");
  const summary = document.querySelector("#summary");
  const searchInput = document.querySelector("#searchInput");
  const premiumThreshold = document.querySelector("#premiumThreshold");
  const turnoverThreshold = document.querySelector("#turnoverThreshold");
  const desiredPurchase = document.querySelector("#desiredPurchase");

  function getSortValue(fund) {
    if (state.sortKey === "executionRank") return getExecution(fund, state).rank;
    return fund[state.sortKey];
  }

  function getVisibleFunds() {
    const keyword = state.search.trim().toLowerCase();
    return funds
      .filter((fund) => {
        const categoryMatch = state.category === "全部" || (state.category === "自选" ? fund.watch : fund.category === state.category);
        const searchMatch = !keyword || fund.name.toLowerCase().includes(keyword) || fund.code.includes(keyword);
        return categoryMatch && searchMatch;
      })
      .sort((a, b) => {
        const av = getSortValue(a);
        const bv = getSortValue(b);
        const result = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv), "zh-CN");
        return state.sortDir === "asc" ? result : -result;
      });
  }

  function renderSortState() {
    document.querySelectorAll("th").forEach((th) => {
      th.classList.toggle("sorted", th.dataset.sort === state.sortKey);
      th.dataset.dir = th.dataset.sort === state.sortKey ? state.sortDir : "";
    });
  }

  function render() {
    const visibleFunds = getVisibleFunds();
    const counts = getExecutionSummary(visibleFunds, state);

    table.innerHTML = renderFundRows(visibleFunds, state);
    summary.textContent = `${visibleFunds.length} 个品种，${counts.executableCount} 个可执行，${counts.watchCount} 个观察`;
    updatedAt.textContent = `更新时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
    renderSortState();
  }

  document.querySelector(".tabs").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    state.category = button.dataset.category;
    document.querySelectorAll(".tabs button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });

  document.querySelector("thead").addEventListener("click", (event) => {
    const th = event.target.closest("th");
    if (!th) return;
    if (state.sortKey === th.dataset.sort) {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = th.dataset.sort;
      state.sortDir = "desc";
    }
    render();
  });

  table.addEventListener("click", (event) => {
    const button = event.target.closest(".watch");
    if (!button) return;
    const fund = funds.find((item) => item.code === button.dataset.code);
    fund.watch = !fund.watch;
    render();
  });

  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value;
    render();
  });

  premiumThreshold.addEventListener("input", (event) => {
    state.premiumThreshold = Number(event.target.value || 0);
    render();
  });

  turnoverThreshold.addEventListener("input", (event) => {
    state.turnoverThreshold = Number(event.target.value || 0);
    render();
  });

  desiredPurchase.addEventListener("input", (event) => {
    state.desiredPurchaseYuan = Number(event.target.value || 0) * 10000;
    render();
  });

  render();
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
