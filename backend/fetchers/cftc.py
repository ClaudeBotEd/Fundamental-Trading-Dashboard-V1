import httpx
from fetchers.base import BaseFetcher

_URL = "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"

_CONTRACTS = [
    ("Gold (XAU)",              "GOLD - COMMODITY EXCHANGE INC."),
    ("Euro (EUR)",              "EURO FX - CHICAGO MERCANTILE EXCHANGE"),
    ("British Pound (GBP)",     "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE"),
    ("Japanese Yen (JPY)",      "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
    ("Australian Dollar (AUD)", "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
    ("Canadian Dollar (CAD)",   "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
    ("Swiss Franc (CHF)",       "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
    ("Bitcoin (BTC)",           "BITCOIN - CHICAGO MERCANTILE EXCHANGE"),
]


class CftcFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        snippets = []
        for display_name, market_name in _CONTRACTS:
            params = {
                "market_and_exchange_names": market_name,
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 2,
            }
            resp = await self._client.get(_URL, params=params)
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                continue
            snippets.append(self._format(display_name, rows))
        return snippets

    @staticmethod
    def _format(display_name: str, rows: list[dict]) -> str:
        def net(row: dict) -> int:
            return int(row["noncomm_positions_long_all"]) - int(row["noncomm_positions_short_all"])

        current_net = net(rows[0])
        date = rows[0].get("report_date_as_yyyy_mm_dd", "")
        lines = [
            f"## COT — {display_name}",
            f"- Date: {date}",
            f"- Non-commercial net: {current_net:+,}",
            f"- Long: {int(rows[0]['noncomm_positions_long_all']):,}",
            f"- Short: {int(rows[0]['noncomm_positions_short_all']):,}",
        ]
        if len(rows) >= 2:
            change = current_net - net(rows[1])
            lines.append(f"- Weekly change: {change:+,}")
        return "\n".join(lines)
