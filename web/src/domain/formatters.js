(function (app) {
  function formatPct(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(value)) return "--";
    const fixed = Number(value).toFixed(digits);
    return value > 0 ? `+${fixed}%` : `${fixed}%`;
  }

  function formatNumber(value, digits = 3) {
    if (value === null || value === undefined || Number.isNaN(value)) return "--";
    return Number(value).toFixed(digits);
  }

  function formatTurnoverYuan(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return "--";
    if (value >= 100000000) return `${(value / 100000000).toFixed(2)}亿`;
    if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
    return `${value.toFixed(0)}元`;
  }

  function formatDepth(fund) {
    if (!fund.askPrice1 || !fund.askVolume1) return "--";
    return formatTurnoverYuan(fund.askPrice1 * fund.askVolume1 * 100);
  }

  function pctClass(value) {
    if (value > 0) return "up";
    if (value < 0) return "down";
    return "flat";
  }

  function confidenceLabel(value) {
    return {
      high: "高",
      medium: "中",
      low: "低",
      none: "无"
    }[value] || value || "--";
  }

  app.formatters = {
    confidenceLabel,
    formatDepth,
    formatNumber,
    formatPct,
    formatTurnoverYuan,
    pctClass
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
