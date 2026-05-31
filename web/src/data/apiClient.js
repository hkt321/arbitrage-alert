(function (app) {
  const API_BASE = "http://127.0.0.1:8000";

  function levelLabel(level) {
    return {
      executable: "可执行",
      watch: "观察",
      normal: "普通",
      unavailable: "不可用"
    }[level] || level || "未知";
  }

  function levelRank(level) {
    return {
      executable: 4,
      watch: 3,
      normal: 2,
      unavailable: 1
    }[level] || 0;
  }

  function mapOpportunity(item) {
    const quote = item.quote || {};
    const valuation = item.valuation || {};
    const execution = item.execution || {};

    return {
      code: item.code,
      name: item.name,
      level: item.level,
      levelLabel: levelLabel(item.level),
      levelRank: levelRank(item.level),
      score: item.score || 0,
      reasons: item.reasons || [],
      purchaseLimitYuan: execution.purchaseLimitYuan,
      marketPrice: quote.market_price,
      priceChangePct: quote.change_pct,
      turnoverYuan: quote.turnover_yuan,
      bidPrice1: quote.bid_price1,
      bidVolume1: quote.bid_volume1,
      askPrice1: quote.ask_price1,
      askVolume1: quote.ask_volume1,
      quoteTime: quote.quote_time,
      model: valuation.model,
      estimatedNav: valuation.estimated_nav,
      grossPremiumPct: valuation.gross_premium_pct,
      tradableEdgePct: valuation.tradable_edge_pct,
      estimatedCostPct: valuation.estimated_cost_pct,
      slippageBufferPct: valuation.slippage_buffer_pct,
      errorBufferPct: valuation.error_buffer_pct,
      confidence: valuation.confidence,
      valuationReasons: valuation.reasons || [],
      inputs: valuation.inputs || {},
      watch: app.watchStore.isWatched(item.code)
    };
  }

  async function fetchOpportunities(options = {}) {
    const params = new URLSearchParams();
    if (options.refresh) params.set("refresh", "true");
    const query = params.toString() ? `?${params.toString()}` : "";

    const response = await fetch(`${API_BASE}/api/opportunities${query}`, {
      headers: { Accept: "application/json" }
    });
    if (!response.ok) {
      throw new Error(`API ${response.status}`);
    }
    const payload = await response.json();
    return {
      data: (payload.data || []).map(mapOpportunity),
      meta: payload.meta || {}
    };
  }

  app.apiClient = {
    fetchOpportunities
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
