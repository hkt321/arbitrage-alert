(function (app) {
  function getExecution(fund, state) {
    const reasons = [];
    const hasPriceEdge = fund.netPremiumPct >= state.premiumThreshold;

    if (fund.tradeStatus !== "正常") reasons.push(fund.tradeStatus);
    if (fund.subscriptionStatus === "暂停") reasons.push("暂停申购");
    if (fund.subscriptionStatus === "限额" && fund.purchaseLimitYuan < state.desiredPurchaseYuan) reasons.push("限额过低");
    if (fund.redemptionStatus !== "开放") reasons.push("赎回受限");
    if (fund.turnover < state.turnoverThreshold) reasons.push("成交额不足");
    if (fund.depthYuan * 100000000 < state.desiredPurchaseYuan) reasons.push("盘口不足");
    if (!hasPriceEdge) reasons.push("净溢价不足");
    if (fund.navLagDays > 1) reasons.push("估值滞后");

    if (hasPriceEdge && reasons.length === 0) {
      return { label: "可执行", rank: 3, reasons: ["额度/流动性满足"] };
    }

    if (fund.premiumPct >= state.premiumThreshold) {
      return { label: "观察", rank: 2, reasons };
    }

    return { label: "普通", rank: 1, reasons: ["未达阈值"] };
  }

  app.executionRules = {
    getExecution
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
