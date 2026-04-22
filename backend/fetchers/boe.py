import httpx
from fetchers.base import BaseFetcher

_URL = (
    "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
    "?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y"
)


class BoEFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        resp = await self._client.get(_URL)
        resp.raise_for_status()
        rows = [
            line.split(",")
            for line in resp.text.strip().splitlines()
            if line and not line.startswith("DATE")
        ]
        valid = [(r[0].strip(), r[1].strip()) for r in rows if len(r) == 2 and r[1].strip()]
        if not valid:
            return []
        date, rate = valid[-1]
        lines = ["## BoE Bank Rate", f"- Current: {rate}%", f"- As of: {date}"]
        if len(valid) >= 2:
            lines.append(f"- Previous: {valid[-2][1]}%")
        return ["\n".join(lines)]
