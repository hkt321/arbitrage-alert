(function (app) {
  const { formatSigned, formatTurnover, formatYuan, pctClass } = app.formatters;
  const { getExecution } = app.executionRules;

  function renderFundRows(funds, state) {
    return funds
      .map((fund) => {
        const execution = getExecution(fund, state);
        const rowClass = execution.label === "可执行" ? "executable" : execution.label === "观察" ? "watching" : "";

        return `
          <tr class="${rowClass}">
            <td>
              <button class="watch ${fund.watch ? "on" : ""}" data-code="${fund.code}" title="切换自选">${fund.watch ? "★" : "☆"}</button>
              <span class="fund-name">${fund.name}</span>
              <span class="fund-code">${fund.code}</span>
            </td>
            <td>
              <span>${fund.nav.toFixed(4)}</span>
              <span class="${pctClass(fund.navChangePct)}">${formatSigned(fund.navChangePct)}</span>
              <small>${fund.navLagDays === 0 ? "当日估值" : `滞后 T-${fund.navLagDays}`}</small>
            </td>
            <td class="premium-cell">
              <strong class="premium ${pctClass(fund.premiumPct)}">${fund.premiumPct.toFixed(2)}%</strong>
              <span>净 ${fund.netPremiumPct.toFixed(2)}%</span>
            </td>
            <td>
              <span>${fund.marketPrice.toFixed(3)}</span>
              <span class="${pctClass(fund.priceChangePct)}">${formatSigned(fund.priceChangePct)}</span>
              <small>价差 ${fund.spreadPct.toFixed(2)}%</small>
            </td>
            <td>
              <span>${formatTurnover(fund.turnover)}</span>
              <small>盘口 ${formatTurnover(fund.depthYuan)}</small>
            </td>
            <td>
              <span>${formatYuan(fund.purchaseLimitYuan)}</span>
              <small>${fund.subscriptionStatus} / 赎回${fund.redemptionStatus}</small>
            </td>
            <td>
              <span>${fund.feePct.toFixed(2)}%</span>
              <small>${fund.settlementCycle}</small>
            </td>
            <td>
              <span class="badge ${execution.label === "可执行" ? "normal" : execution.label === "观察" ? "risk" : "quiet"}">${execution.label}</span>
              <small>${execution.reasons.slice(0, 2).join("、")}</small>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function getExecutionSummary(funds, state) {
    const executions = funds.map((fund) => getExecution(fund, state));
    return {
      executableCount: executions.filter((item) => item.label === "可执行").length,
      watchCount: executions.filter((item) => item.label === "观察").length
    };
  }

  app.tableView = {
    renderFundRows,
    getExecutionSummary
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
