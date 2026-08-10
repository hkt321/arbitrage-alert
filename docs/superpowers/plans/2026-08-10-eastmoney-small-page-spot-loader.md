# Eastmoney Small-Page LOF Spot Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the failing AkShare full-market LOF quote request with a validated 20-row direct Eastmoney paginator while retaining AkShare for official NAV and purchase/redemption data.

**Architecture:** A focused `EastmoneyLofSpotLoader` owns direct, proxy-free paginated quote requests and returns the same minimal DataFrame columns consumed by `AkshareLofProvider`. The existing provider continues to merge quotes with `ak.fund_purchase_em()` and the CLI remains watch-only. Partial or structurally invalid markets fail closed before any notification.

**Tech Stack:** Python 3.12, standard-library `urllib`, pandas supplied transitively by `akshare==1.18.83`, standard-library `unittest`.

## Global Constraints

- Keep `akshare==1.18.83` as the only direct dependency.
- Request exactly 20 quote rows per page and only `f2,f3,f5,f6,f8,f12,f14`.
- Quote requests must not inherit process proxy settings or modify permanent environment variables.
- Use one request per page, with no alternate host and no application-level retry.
- Any incomplete, duplicate, malformed, or HTTP-failed market must raise `DataSourceError` and prevent notification.
- Do not add caching, databases, dashboards, historical statistics, estimated NAV, or execution labels.

---

### Task 1: Direct Small-Page Quote Loader

**Files:**
- Create: `backend/app/providers/errors.py`
- Create: `backend/app/providers/eastmoney_lof_spot_loader.py`
- Modify: `backend/app/providers/akshare_lof_provider.py`
- Create: `tests/test_eastmoney_lof_spot_loader.py`

**Interfaces:**
- Produces: `DataSourceError(RuntimeError)` in `app.providers.errors`.
- Produces: `EastmoneyLofSpotLoader(page_size: int = 20, timeout: int = 15, open_url: Callable | None = None)`.
- Produces: `EastmoneyLofSpotLoader.fetch_all() -> pandas.DataFrame` with columns `代码, 名称, 最新价, 涨跌幅, 成交量, 成交额, 换手率`.
- Preserves: importing `DataSourceError` from `akshare_lof_provider.py` for current callers.

- [ ] **Step 1: Write paginator behavior tests**

Create a fake opener whose response payloads are selected by the `pn` query parameter. Use a first payload with `total=3` and two rows, then a second payload with one row. Assert the output code order and exact mapped values:

```python
loader = EastmoneyLofSpotLoader(page_size=2, open_url=fake_open)
frame = loader.fetch_all()

self.assertEqual(requested_pages, [1, 2])
self.assertEqual(frame["代码"].tolist(), ["501001", "161001", "501002"])
self.assertEqual(frame.loc[0, "最新价"], 1.2)
self.assertEqual(
    frame.columns.tolist(),
    ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"],
)
```

- [ ] **Step 2: Write fail-closed tests**

Add separate tests asserting `DataSourceError` for:

```python
with self.assertRaisesRegex(DataSourceError, "第 2 页记录数不符"):
    loader_with_empty_second_page.fetch_all()

with self.assertRaisesRegex(DataSourceError, "行情存在重复代码: 501001"):
    loader_with_duplicate_code.fetch_all()

with self.assertRaisesRegex(DataSourceError, "行情总数不符"):
    loader_with_wrong_total.fetch_all()

with self.assertRaisesRegex(DataSourceError, "Eastmoney 行情 HTTP 500"):
    loader_with_http_500.fetch_all()
```

- [ ] **Step 3: Run the new tests and verify RED**

Run: `python -m unittest tests.test_eastmoney_lof_spot_loader -v`

Expected: import failure because `eastmoney_lof_spot_loader` does not exist.

- [ ] **Step 4: Add the shared error type**

Create `errors.py`:

```python
class DataSourceError(RuntimeError):
    """A remote response cannot be used safely for reminders."""
```

Replace the local definition in `akshare_lof_provider.py` with:

```python
from .errors import DataSourceError
```

- [ ] **Step 5: Implement the minimal paginator**

Use these fixed request values:

```python
URL = "https://88.push2.eastmoney.com/api/qt/clist/get"
MARKETS = "b:MK0404,b:MK0405,b:MK0406,b:MK0407"
FIELDS = "f2,f3,f5,f6,f8,f12,f14"
```

Build the default opener with `build_opener(ProxyHandler({})).open`. For page 1, require a positive integer `data.total` and a list `data.diff`; compute `ceil(total / page_size)`. Require each page to return `min(page_size, total - already_collected)` rows. After all pages, require the collected row count and unique `f12` count to both equal `total`. Map fields as follows:

```python
FIELD_MAP = {
    "f12": "代码",
    "f14": "名称",
    "f2": "最新价",
    "f3": "涨跌幅",
    "f5": "成交量",
    "f6": "成交额",
    "f8": "换手率",
}
```

Convert the five numeric output columns with `pandas.to_numeric(errors="coerce")`. Wrap URL, HTTP, JSON, and schema exceptions in `DataSourceError` with the page number and no response body or proxy value.

- [ ] **Step 6: Run loader tests and full tests**

Run: `python -m unittest tests.test_eastmoney_lof_spot_loader -v`

Expected: all new tests pass.

Run: `python -m unittest discover -v`

Expected: all existing 13 tests plus new loader tests pass.

- [ ] **Step 7: Commit Task 1**

```powershell
git add backend/app/providers/errors.py backend/app/providers/eastmoney_lof_spot_loader.py backend/app/providers/akshare_lof_provider.py tests/test_eastmoney_lof_spot_loader.py
git commit -m "feat: add small-page LOF quote loader"
```

---

### Task 2: Make the Small-Page Loader the Default Quote Source

**Files:**
- Modify: `backend/app/providers/akshare_lof_provider.py`
- Modify: `tests/test_akshare_lof_provider.py`
- Modify: `tools/run_check.py`
- Modify: `requirements.txt`
- Modify: `.github/workflows/daily-check.yml`
- Modify: `README.md`
- Modify: `docs/USAGE.md`

**Interfaces:**
- Consumes: `EastmoneyLofSpotLoader().fetch_all() -> pandas.DataFrame`.
- Preserves: `AkshareLofProvider(spot_loader=None, purchase_loader=None).fetch_all() -> list[LofSnapshot]`.
- Preserves: CLI arguments `--top`, `--min-limit`, `--min-premium`, `--min-discount`, `--json`, and `--push-key`.

- [ ] **Step 1: Write the default-wiring test**

Patch `EastmoneyLofSpotLoader` and `akshare.fund_purchase_em`, return complete local DataFrames, construct `AkshareLofProvider()` without injected loaders, and assert the resulting `LofSnapshot` contains the expected code, price, NAV, NAV date, and premium. The behavior assertion—not mock call count—is the acceptance signal.

- [ ] **Step 2: Run the wiring test and verify RED**

Run: `python -m unittest tests.test_akshare_lof_provider.AkshareLofProviderTests.test_default_provider_uses_small_page_quote_loader -v`

Expected: failure because the provider still defaults to `ak.fund_lof_spot_em`.

- [ ] **Step 3: Replace only the default spot loader**

Change the constructor default selection to:

```python
self._spot_loader = spot_loader or EastmoneyLofSpotLoader().fetch_all
if purchase_loader is None:
    import akshare as ak
    purchase_loader = ak.fund_purchase_em
self._purchase_loader = purchase_loader
```

Do not change injection behavior or the quote/NAV merge rules.

- [ ] **Step 4: Run provider and CLI tests**

Run: `python -m unittest tests.test_akshare_lof_provider tests.test_run_check -v`

Expected: all provider and watch-only CLI tests pass; no result level equals `executable`.

- [ ] **Step 5: Verify configuration and documentation changes**

Confirm `requirements.txt` has exactly one non-comment line, `akshare==1.18.83`. Confirm Actions installs that file before invoking the unchanged CLI arguments. Confirm README and usage documentation state that quotes use a small-page Eastmoney loader, while AkShare supplies official NAV and purchase/redemption information.

- [ ] **Step 6: Commit Task 2**

```powershell
git add backend/app/providers/akshare_lof_provider.py tests/test_akshare_lof_provider.py tools/run_check.py requirements.txt .github/workflows/daily-check.yml README.md docs/USAGE.md docs/superpowers/plans/2026-08-10-eastmoney-small-page-spot-loader.md
git commit -m "feat: switch alerts to validated LOF data"
```

---

### Task 3: Trading-Window Gate and Duplicate Collector Removal

**Files:**
- Delete after live PASS: `backend/app/providers/palmmicro_lof_provider.py`
- Delete after live PASS: `backend/app/providers/eastmoney_fund_status_provider.py`
- Delete after live PASS: `backend/app/models/palmmicro_lof.py`
- Delete after live PASS: `backend/app/models/fund_status.py`
- Inspect: all repository Python and Markdown files for live imports or runtime references.

**Interfaces:**
- Consumes: the complete CLI from Task 2.
- Produces: one active quote loader and one active official-NAV/status loader, with no old runtime imports.

- [ ] **Step 1: Run the complete offline gate**

Run:

```powershell
python -m unittest discover -v
python -m compileall -q backend tools tests
git diff --check
```

Expected: zero failures and exit code 0 for all commands.

- [ ] **Step 2: Verify the full quote market during trading hours**

Run a read-only provider check without SendKey:

```powershell
python -c "from backend.app.providers.eastmoney_lof_spot_loader import EastmoneyLofSpotLoader; frame=EastmoneyLofSpotLoader().fetch_all(); print('rows', len(frame)); print('unique', frame['代码'].nunique()); print('priced', frame['最新价'].notna().sum())"
```

Acceptance: exit 0; `rows == unique`; `rows > 100`; `priced > 0`.

- [ ] **Step 3: Verify the merged watch-only CLI during trading hours**

Run: `python tools/run_check.py --top 5 --json`

Acceptance: exit 0; JSON contains five non-empty items; each item has `price`, `latest_nav`, `nav_date`, and `premium_basis=latest_official_nav`; every `level` is one of `watch`, `normal`, or `unknown`; no notification is sent.

- [ ] **Step 4: Stop on live failure**

If either live command fails or violates an acceptance count, do not delete old files and do not claim replacement PASS. Record the exact failing command, exit code, and sanitized error, then stop for user direction.

- [ ] **Step 5: Delete old collectors only after live PASS**

First run:

```powershell
rg -n "PalmmicroLofProvider|PalmmicroLofSnapshot|EastmoneyFundStatusProvider|FundStatus|palmmicro_lof_provider|eastmoney_fund_status_provider" backend tools tests
```

Remove any obsolete runtime imports found, then delete the four named provider/model files. Do not modify historical design or roadmap documents solely because they describe earlier decisions.

- [ ] **Step 6: Run final verification after deletion**

Run:

```powershell
python -m unittest discover -v
python -m compileall -q backend tools tests
git diff --check
git status --short --branch
```

Expected: all tests pass, compile and diff checks exit 0, and only intended implementation files are changed.

- [ ] **Step 7: Commit cleanup**

```powershell
git add -A backend/app/providers backend/app/models tests tools README.md docs/USAGE.md requirements.txt .github/workflows/daily-check.yml
git commit -m "refactor: remove duplicate LOF collectors"
```

- [ ] **Step 8: Do not push**

Leave `codex/akshare-lightweight-alert` local. Report the three commit IDs, test count, live market counts, and exact no-push state to the user.
