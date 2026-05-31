(function (app) {
  const {
    confidenceLabel,
    formatDepth,
    formatNumber,
    formatPct,
    formatTurnoverYuan,
    pctClass
  } = app.formatters;

  function rowClass(fund) {
    if (fund.level === "executable") return "executable";
    if (fund.level === "watch") return "watching";
    return "";
  }

  function badgeClass(fund) {
    if (fund.level === "executable") return "normal";
    if (fund.level === "watch") return "risk";
    return "quiet";
  }

  function renderReasonList(reasons) {
    if (!reasons || reasons.length === 0) return "暂无阻断";
    return reasons.slice(0, 3).join("、");
  }

  function renderFundRows(funds) {
    if (funds.length === 0) {
      return `<tr><td colspan="8" class="empty-state">没有匹配的品种</td></tr>`;
    }

    return funds
      .map((fund) => {
        return `
          <tr class="${rowClass(fund)}">
            <td>
              <button class="watch ${fund.watch ? "on" : ""}" data-code="${fund.code}" title="切换自选">${fund.watch ? "★" : "☆"}</button>
              <span class="fund-name">${fund.name}</span>
              <span class="fund-code">${fund.code}</span>
            </td>
            <td>
              <span>${formatNumber(fund.estimatedNav, 4)}</span>
              <small>${fund.model || "--"}</small>
            </td>
            <td class="premium-cell">
              <strong class="premium ${pctClass(fund.grossPremiumPct)}">${formatPct(fund.grossPremiumPct)}</strong>
              <span>净 ${formatPct(fund.tradableEdgePct)}</span>
            </td>
            <td>
              <span>${formatNumber(fund.marketPrice, 3)}</span>
              <span class="${pctClass(fund.priceChangePct)}">${formatPct(fund.priceChangePct)}</span>
              <small>买一 ${formatNumber(fund.bidPrice1, 3)} / 卖一 ${formatNumber(fund.askPrice1, 3)}</small>
            </td>
            <td>
              <span>${formatTurnoverYuan(fund.turnoverYuan)}</span>
              <small>卖一深度 ${formatDepth(fund)}</small>
            </td>
            <td>
              <span class="${pctClass(fund.tradableEdgePct)}">${formatPct(fund.tradableEdgePct)}</span>
              <small>成本 ${formatPct(fund.estimatedCostPct)} / 误差 ${formatPct(fund.errorBufferPct)}</small>
            </td>
            <td>
              <span>${confidenceLabel(fund.confidence)}</span>
              <small>${fund.inputs?.benchmarkSignalId || "无信号"}</small>
            </td>
            <td>
              <span class="badge ${badgeClass(fund)}">${fund.levelLabel}</span>
              <small>${renderReasonList(fund.reasons)}</small>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function getExecutionSummary(funds) {
    return {
      executableCount: funds.filter((item) => item.level === "executable").length,
      watchCount: funds.filter((item) => item.level === "watch").length,
      unavailableCount: funds.filter((item) => item.level === "unavailable").length
    };
  }

  app.tableView = {
    getExecutionSummary,
    renderFundRows
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
