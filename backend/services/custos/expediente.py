from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo


class Expediente:
    """Working hours of the company: only this part of an incident costs productivity."""

    @staticmethod
    def segundos_uteis(intervalos, empresa):
        """Seconds of the (UTC, naive) intervals that fall inside the working hours, without double
        counting overlaps. Uses the company's time zone, so DST and the local date are respected."""
        tz, utc = ZoneInfo(empresa.fuso), timezone.utc
        days = {int(d) for d in empresa.expediente_dias}
        start_t, end_t = time.fromisoformat(empresa.expediente_inicio), time.fromisoformat(empresa.expediente_fim)
        merged = []
        for s, e in sorted((s, e) for s, e in intervalos if e > s):
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        total = 0.0
        for s, e in merged:
            s, e = s.replace(tzinfo=utc), e.replace(tzinfo=utc)
            day, last = s.astimezone(tz).date() - timedelta(days=1), e.astimezone(tz).date()
            while day <= last:
                if day.isoweekday() in days:
                    ws = datetime.combine(day, start_t, tz).astimezone(utc)
                    we = datetime.combine(day, end_t, tz).astimezone(utc)
                    total += max(0.0, (min(e, we) - max(s, ws)).total_seconds())
                day += timedelta(days=1)
        return Decimal(round(total))
