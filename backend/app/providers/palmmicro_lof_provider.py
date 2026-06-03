import re
import time
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.models.palmmicro_lof import PalmmicroLofSnapshot

BASE_URL = "https://palmmicro.com/woody/res/"


class PalmmicroLofProvider:
    """Fetch LOF fund data from palmmicro.com."""

    REQUEST_DELAY = 0.5

    def __init__(self, request_delay: float = 0.5, timeout: int = 15) -> None:
        self.request_delay = request_delay
        self.timeout = timeout
        self._last_request = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_all_funds(self) -> list[PalmmicroLofSnapshot]:
        html = self._fetch("lofcn.php")
        return self._parse_estimation_table(html) if html else []

    def fetch_detail(self, code: str) -> PalmmicroLofSnapshot | None:
        html = self._fetch(self._detail_url(code))
        return self._parse_detail(html) if html else None

    def fetch_all_with_details(
        self, top_n: int = 20, min_abs_premium: float = 0
    ) -> list[PalmmicroLofSnapshot]:
        funds = self.fetch_all_funds()

        def abs_prem(f):
            p = f.realtime_premium_pct if f.realtime_premium_pct is not None else f.est_premium_pct
            return abs(p) if p is not None else 0

        funds.sort(key=abs_prem, reverse=True)
        candidates = [f for f in funds if abs_prem(f) >= min_abs_premium][:top_n]
        enriched = []

        for fund in candidates:
            detail = self.fetch_detail(fund.code)
            if detail:
                if detail.price is not None:
                    fund.price = detail.price
                    fund.price_change_pct = detail.price_change_pct
                if detail.shares_wan is not None:
                    fund.shares_wan = detail.shares_wan
                    fund.shares_delta_wan = detail.shares_delta_wan
                    fund.volume = detail.volume
                    fund.turnover_pct = detail.turnover_pct
                if detail.bid_price1 is not None:
                    fund.bid_price1 = detail.bid_price1
                    fund.bid_volume1 = detail.bid_volume1
                    fund.ask_price1 = detail.ask_price1
                    fund.ask_volume1 = detail.ask_volume1
            enriched.append(fund)

        return enriched

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _fetch(self, relative_url: str) -> str | None:
        elapsed = time.time() - self._last_request
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        url = urljoin(BASE_URL, relative_url)
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            self._last_request = time.time()
            return html
        except Exception as exc:
            import sys
            print(f"[PalmmicroLofProvider] {url}: {exc}", file=sys.stderr)
            return None

    @staticmethod
    def _detail_url(code: str) -> str:
        code = code.upper().replace(".", "")
        ex = "sh" if code.startswith("SH") else "sz" if code.startswith("SZ") else "sh"
        fc = code[2:] if code.startswith(("SH", "SZ")) else code
        return f"{ex}{fc}cn.php"

    # ------------------------------------------------------------------
    # Main page: estimationtable
    # ------------------------------------------------------------------

    def _parse_estimation_table(self, html: str) -> list[PalmmicroLofSnapshot]:
        results: list[PalmmicroLofSnapshot] = []
        m = re.search(r'<TABLE[^>]*id="estimationtable"[^>]*>(.*?)</TABLE>', html, re.S)
        if not m:
            return results

        for row in re.findall(r'<(?:TR|tr)>(.*?)</(?:TR|tr)>', m.group(1), re.S):
            cells = self._row_cells(row)
            if not cells:
                continue
            code, name = self._parse_code_cell(cells[0])
            if not code:
                continue

            nav_text = self._ctext(cells[1]) if len(cells) > 1 else ""
            date_text = self._ctext(cells[2]) if len(cells) > 2 else ""
            prem_text = self._ctext(cells[3]) if len(cells) > 3 else ""

            snapshot = PalmmicroLofSnapshot(
                code=code, name=name,
                est_nav=self._num(nav_text), est_date=date_text or None,
                est_premium_pct=self._pct(prem_text),
            )

            if len(cells) >= 6:
                rn = self._ctext(cells[4])
                rp = self._ctext(cells[5])
                if rn:
                    snapshot.realtime_nav = self._num(rn)
                if rp:
                    snapshot.realtime_premium_pct = self._pct(rp)
            if len(cells) >= 8:
                rn = self._ctext(cells[6])
                rp = self._ctext(cells[7])
                if rn:
                    snapshot.realtime_nav = self._num(rn)
                if rp:
                    snapshot.realtime_premium_pct = self._pct(rp)

            results.append(snapshot)

        return results

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def _parse_detail(self, html: str) -> PalmmicroLofSnapshot | None:
        snapshot = PalmmicroLofSnapshot(
            code=self._extract_code(html),
            name=self._extract_title(html),
        )
        if not snapshot.code and not snapshot.name:
            return None

        # Fund share table
        for row in self._trows(html, "fundsharetable"):
            cells = self._row_cells(row)
            if len(cells) >= 5:
                shares = self._num(self._ctext(cells[1]))
                delta = self._num(self._ctext(cells[2]))
                vol = self._vol(self._ctext(cells[3]))
                turn = self._pct(self._ctext(cells[4]))
                if shares is not None:
                    snapshot.shares_wan = shares
                    snapshot.shares_delta_wan = delta
                    snapshot.volume = vol
                    snapshot.turnover_pct = turn
                    break

        # Trading table (5-level)
        for row in self._trows(html, "tradingtable"):
            cells = self._row_cells(row)
            if len(cells) >= 2:
                label = self._ctext(cells[0]).strip()
                price = self._num(self._ctext(cells[1]))
                vol = self._vol(self._ctext(cells[2])) if len(cells) > 2 else 0
                if label in ("卖1", "Sell1"):
                    snapshot.ask_price1, snapshot.ask_volume1 = price, vol
                elif label in ("买1", "Buy1"):
                    snapshot.bid_price1, snapshot.bid_volume1 = price, vol

        # Reference table (price)
        code_upper = snapshot.code.replace(".", "").upper()
        for row in self._trows(html, "referencetable"):
            cells = self._row_cells(row)
            if len(cells) >= 3 and code_upper in self._ctext(cells[0]).upper():
                snapshot.price = self._num(self._ctext(cells[1]))
                snapshot.price_change_pct = self._pct(self._ctext(cells[2]))
                break

        return snapshot

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _trows(html: str, table_id: str) -> list[str]:
        m = re.search(rf'<TABLE[^>]*id="{re.escape(table_id)}"[^>]*>(.*?)</TABLE>', html, re.S)
        if not m:
            return []
        tc = m.group(1)
        tbody = re.search(r'<(?:TBODY|tbody)>(.*?)</(?:TBODY|tbody)>', tc, re.S)
        inner = tbody.group(1) if tbody else tc
        return re.findall(r'<(?:TR|tr)>(.*?)</(?:TR|tr)>', inner, re.S)

    @staticmethod
    def _row_cells(row: str) -> list[str]:
        """Return full TD/td tags (with attributes)."""
        return re.findall(r'(<(?:TD|td)[^>]*>.*?</(?:TD|td)>)', row, re.S)

    @staticmethod
    def _ctext(tag: str) -> str:
        """Strip HTML from a full TD tag."""
        s = re.sub(r'<[^>]+>', '', tag).strip()
        return s

    @staticmethod
    def _ctitle(tag: str) -> str:
        """Get title attribute from a TD full tag."""
        m = re.search(r'title="([^"]*)"', tag, re.I)
        return m.group(1) if m else ""

    def _parse_code_cell(self, tag: str) -> tuple[str, str]:
        """Extract code+name from a full TD tag (may have title=)."""
        name = self._ctitle(tag)
        text = self._ctext(tag)
        if not text:
            return "", ""
        return text, name

    @staticmethod
    def _num(text: str) -> float | None:
        text = text.strip().replace(",", "")
        try:
            return float(text) if text else None
        except ValueError:
            return None

    @staticmethod
    def _pct(text: str) -> float | None:
        text = text.strip().replace("%", "").replace(",", "")
        try:
            return float(text) if text else None
        except ValueError:
            return None

    @staticmethod
    def _vol(text: str) -> int | None:
        text = text.strip().replace(",", "")
        try:
            return int(float(text)) if text else None
        except ValueError:
            return None

    @staticmethod
    def _extract_title(html: str) -> str:
        m = re.search(r'<(?:H1|h1)>(.*?)</(?:H1|h1)>', html, re.S)
        if not m:
            return ""
        text = m.group(1)
        bracket = text.find("【")
        return text[:bracket] if bracket > 0 else text.strip()

    @staticmethod
    def _extract_code(html: str) -> str:
        m = re.search(r'<(?:H1|h1)>(.*?)</(?:H1|h1)>', html, re.S)
        if m:
            cm = re.search(r'【([^】]+)】', m.group(1))
            if cm:
                return cm.group(1)
        return ""