(function (app) {
  function formatSigned(value) {
    const fixed = value.toFixed(2);
    return value > 0 ? `+${fixed}%` : `${fixed}%`;
  }

  function formatTurnover(value) {
    return value >= 0.1 ? `${value.toFixed(2)}亿` : `${(value * 10000).toFixed(0)}万`;
  }

  function formatYuan(value) {
    if (value === null || value === undefined) return "未披露";
    if (value === 0) return "不可申购";
    if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
    if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
    return `${value.toFixed(0)}元`;
  }

  function pctClass(value) {
    if (value > 0) return "up";
    if (value < 0) return "down";
    return "flat";
  }

  app.formatters = {
    formatSigned,
    formatTurnover,
    formatYuan,
    pctClass
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
