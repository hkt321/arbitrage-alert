(function (app) {
  const SETTINGS_KEY = "arbitrage-alert-notification-settings";
  const HISTORY_KEY = "arbitrage-alert-notification-history";

  const levelRank = {
    executable: 4,
    watch: 3,
    normal: 2,
    unavailable: 1
  };

  const defaultSettings = {
    enabled: false,
    minLevel: "executable",
    cooldownMinutes: 10
  };

  function readJson(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  }

  function writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function getSettings() {
    return { ...defaultSettings, ...readJson(SETTINGS_KEY, defaultSettings) };
  }

  function saveSettings(settings) {
    writeJson(SETTINGS_KEY, { ...getSettings(), ...settings });
  }

  function canNotify() {
    return "Notification" in window;
  }

  async function requestPermission() {
    if (!canNotify()) return "unsupported";
    if (Notification.permission === "granted") return "granted";
    if (Notification.permission === "denied") return "denied";
    return Notification.requestPermission();
  }

  function shouldNotify(fund, settings, history, now) {
    if (!settings.enabled) return false;
    if ((levelRank[fund.level] || 0) < (levelRank[settings.minLevel] || 0)) return false;

    const key = `${fund.code}:${fund.level}`;
    const last = history[key] || 0;
    const cooldownMs = Math.max(Number(settings.cooldownMinutes || 10), 1) * 60 * 1000;
    return now - last >= cooldownMs;
  }

  function buildMessage(fund) {
    const edge = fund.tradableEdgePct === null || fund.tradableEdgePct === undefined
      ? "--"
      : `${fund.tradableEdgePct.toFixed(2)}%`;
    const premium = fund.grossPremiumPct === null || fund.grossPremiumPct === undefined
      ? "--"
      : `${fund.grossPremiumPct.toFixed(2)}%`;
    const reason = fund.reasons && fund.reasons.length ? fund.reasons[0] : "达到提醒条件";
    return `溢价 ${premium}，边际 ${edge}。${reason}`;
  }

  function notify(fund) {
    const notification = new Notification(`${fund.levelLabel}: ${fund.name}`, {
      body: buildMessage(fund),
      tag: `arbitrage-alert-${fund.code}`,
      requireInteraction: fund.level === "executable"
    });

    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  }

  function process(funds, options = {}) {
    const settings = getSettings();
    if (!settings.enabled || options.cached) return 0;
    if (!canNotify() || Notification.permission !== "granted") return 0;

    const history = readJson(HISTORY_KEY, {});
    const now = Date.now();
    let count = 0;

    funds.forEach((fund) => {
      if (!shouldNotify(fund, settings, history, now)) return;
      notify(fund);
      history[`${fund.code}:${fund.level}`] = now;
      count += 1;
    });

    writeJson(HISTORY_KEY, history);
    return count;
  }

  app.notifier = {
    canNotify,
    getSettings,
    process,
    requestPermission,
    saveSettings
  };
})(window.ArbitrageAlert = window.ArbitrageAlert || {});
