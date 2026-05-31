(function (app) {
  const { fetchOpportunities } = app.apiClient;
  const { getExecutionSummary, renderFundRows } = app.tableView;
  const notifier = app.notifier;

  const state = {
    autoRefresh: false,
    category: "全部",
    funds: [],
    lastMeta: {},
    lastSource: "api",
    refreshIntervalSeconds: 60,
    search: "",
    sortDir: "desc",
    sortKey: "grossPremiumPct"
  };

  let refreshTimer = null;

  const table = document.querySelector("#fundTable");
  const updatedAt = document.querySelector("#updatedAt");
  const summary = document.querySelector("#summary");
  const searchInput = document.querySelector("#searchInput");
  const refreshButton = document.querySelector("#refreshButton");
  const autoRefresh = document.querySelector("#autoRefresh");
  const refreshInterval = document.querySelector("#refreshInterval");
  const notificationButton = document.querySelector("#notificationButton");
  const notificationLevel = document.querySelector("#notificationLevel");
  const notificationCooldown = document.querySelector("#notificationCooldown");

  app.watchStore = {
    key: "arbitrage-alert-watchlist",
    read() {
      try {
        return new Set(JSON.parse(localStorage.getItem(this.key) || "[]"));
      } catch {
        return new Set();
      }
    },
    write(items) {
      localStorage.setItem(this.key, JSON.stringify([...items]));
    },
    isWatched(code) {
      return this.read().has(code);
    },
    toggle(code) {
      const items = this.read();
      if (items.has(code)) items.delete(code);
      else items.add(code);
      this.write(items);
      return items.has(code);
    }
  };

  function getSortValue(fund) {
    return fund[state.sortKey];
  }

  function categoryMatches(fund) {
    if (state.category === "全部") return true;
    if (state.category === "自选") return fund.watch;
    return fund.levelLabel === state.category;
  }

  function getVisibleFunds() {
    const keyword = state.search.trim().toLowerCase();
    return state.funds
      .filter((fund) => {
        const searchMatch =
          !keyword ||
          fund.name.toLowerCase().includes(keyword) ||
          fund.code.toLowerCase().includes(keyword);
        return categoryMatches(fund) && searchMatch;
      })
      .sort((a, b) => {
        const av = getSortValue(a);
        const bv = getSortValue(b);
        const result = typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av ?? "").localeCompare(String(bv ?? ""), "zh-CN");
        return state.sortDir === "asc" ? result : -result;
      });
  }

  function renderSortState() {
    document.querySelectorAll("th").forEach((th) => {
      th.classList.toggle("sorted", th.dataset.sort === state.sortKey);
      th.dataset.dir = th.dataset.sort === state.sortKey ? state.sortDir : "";
    });
  }

  function renderNotificationControls() {
    const settings = notifier.getSettings();
    notificationLevel.value = settings.minLevel;
    notificationCooldown.value = settings.cooldownMinutes;

    if (!notifier.canNotify()) {
      notificationButton.textContent = "通知不可用";
      notificationButton.disabled = true;
      return;
    }

    if (Notification.permission === "granted" && settings.enabled) {
      notificationButton.textContent = "通知已启用";
      notificationButton.classList.add("active");
      return;
    }

    if (Notification.permission === "denied") {
      notificationButton.textContent = "通知被拒绝";
      notificationButton.disabled = true;
      return;
    }

    notificationButton.textContent = "启用通知";
    notificationButton.classList.remove("active");
  }

  function render() {
    const visibleFunds = getVisibleFunds();
    const counts = getExecutionSummary(visibleFunds);

    table.innerHTML = renderFundRows(visibleFunds);
    summary.textContent = `${visibleFunds.length} 个品种，${counts.executableCount} 个可执行，${counts.watchCount} 个观察，${counts.unavailableCount} 个不可用`;
    renderSortState();
    renderNotificationControls();
  }

  function setStatus(message) {
    updatedAt.textContent = message;
  }

  function updateNotificationSettings() {
    notifier.saveSettings({
      minLevel: notificationLevel.value,
      cooldownMinutes: Number(notificationCooldown.value || 10)
    });
  }

  function processNotifications() {
    const count = notifier.process(state.funds, {
      cached: Boolean(state.lastMeta.cached)
    });
    if (count > 0) {
      const current = updatedAt.textContent;
      setStatus(`${current}，已发送 ${count} 条通知`);
    }
  }

  async function loadData(options = {}) {
    refreshButton.disabled = true;
    setStatus(options.refresh ? "正在刷新真实行情..." : "正在加载机会列表...");
    try {
      const payload = await fetchOpportunities({ refresh: options.refresh });
      state.funds = payload.data;
      state.lastMeta = payload.meta || {};
      state.lastSource = "api";
      const cacheText = state.lastMeta.cached ? "缓存" : "实时";
      const asOf = state.lastMeta.asOf
        ? new Date(state.lastMeta.asOf).toLocaleString("zh-CN", { hour12: false })
        : new Date().toLocaleString("zh-CN", { hour12: false });
      setStatus(`更新时间：${asOf}（${cacheText}）`);
      processNotifications();
    } catch (error) {
      state.funds = app.mockFunds || [];
      state.lastSource = "mock";
      setStatus(`API 暂不可用，显示本地样例：${error.message}`);
    } finally {
      refreshButton.disabled = false;
      render();
    }
  }

  function scheduleRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = null;
    if (!state.autoRefresh) return;

    const intervalMs = Math.max(state.refreshIntervalSeconds, 15) * 1000;
    refreshTimer = setInterval(() => loadData({ refresh: true }), intervalMs);
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
    const watched = app.watchStore.toggle(button.dataset.code);
    const fund = state.funds.find((item) => item.code === button.dataset.code);
    if (fund) fund.watch = watched;
    render();
  });

  searchInput.addEventListener("input", (event) => {
    state.search = event.target.value;
    render();
  });

  refreshButton.addEventListener("click", () => loadData({ refresh: true }));

  autoRefresh.addEventListener("change", (event) => {
    state.autoRefresh = event.target.checked;
    scheduleRefresh();
  });

  refreshInterval.addEventListener("input", (event) => {
    state.refreshIntervalSeconds = Number(event.target.value || 60);
    scheduleRefresh();
  });

  notificationButton.addEventListener("click", async () => {
    updateNotificationSettings();
    const permission = await notifier.requestPermission();
    notifier.saveSettings({ enabled: permission === "granted" });
    renderNotificationControls();
  });

  notificationLevel.addEventListener("change", updateNotificationSettings);
  notificationCooldown.addEventListener("input", updateNotificationSettings);

  renderNotificationControls();
  loadData();
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
