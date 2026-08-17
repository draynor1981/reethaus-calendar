#!/usr/bin/env python3
"""
Reethaus / Flussbad program -> ICS calendar feed.

Scrapes https://slowness.com/calendar/ and writes reethaus.ics
containing all upcoming events whose venue mentions Reethaus or Flussbad.

Designed to be structure-tolerant: instead of relying on WordPress CSS
class names (which change on redesigns), it walks all <h3> headings and
looks for a date/time pattern in the surrounding text.
"""

import re
import sys
import hashlib
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

CALENDAR_URL = "https://slowness.com/calendar/"
OUTPUT_FILE = "reethaus.ics"

# Only keep events at these venues (case-insensitive substring match)
VENUE_KEYWORDS = ("reethaus", "flussbad")

DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})")

# Minimal VTIMEZONE for Europe/Berlin so Apple Calendar shows correct
# local times regardless of the subscriber's timezone.
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def ics_escape(text: str) -> str:
    """Escape text per RFC 5545."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Fold long lines at 75 octets per RFC 5545."""
    if len(line.encode("utf-8")) <= 75:
        return line
    out, cur = [], ""
    for ch in line:
        if len((cur + ch).encode("utf-8")) > 74:
            out.append(cur)
            cur = " " + ch  # continuation lines start with a space
        else:
            cur += ch
    out.append(cur)
    return "\r\n".join(out)


def fetch_page() -> str:
    resp = requests.get(
        CALENDAR_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; reethaus-ics/1.0)"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def extract_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()

    for heading in soup.find_all("h3"):
        title = " ".join(heading.get_text(" ", strip=True).split())
        if not title:
            continue

        # Collect the text of the event "card": walk up from the heading
        # one level at a time, stopping as soon as the container's text
        # contains a date. This keeps the container as tight as possible
        # so we never pick up a neighbouring event's venue or dates.
        container = heading
        block_text = ""
        for _ in range(6):
            if container.parent is None:
                break
            container = container.parent
            block_text = " ".join(container.get_text(" ", strip=True).split())
            if DATE_RE.search(block_text):
                break

        # Restrict the searched text to a window after the title so that,
        # if the walk still grabbed too large a container, we don't pick
        # up a neighbouring event's dates.
        idx = block_text.find(title)
        window = block_text[idx : idx + 600] if idx >= 0 else block_text[:600]

        dates = DATE_RE.findall(window)
        if not dates:
            continue

        # Venue filter
        if not any(k in window.lower() for k in VENUE_KEYWORDS):
            continue

        d, m, y = dates[0]
        start_date = date(int(y), int(m), int(d))
        end_date = start_date
        if len(dates) >= 2:
            d2, m2, y2 = dates[1]
            end_date = date(int(y2), int(m2), int(d2))

        tm = TIME_RE.search(window)
        start_dt = end_dt = None
        if tm:
            h1, min1, h2, min2 = (int(x) for x in tm.groups())
            start_dt = datetime(start_date.year, start_date.month, start_date.day, h1, min1)
            end_dt = datetime(end_date.year, end_date.month, end_date.day, h2, min2)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

        # Try to find an RSVP / detail link inside the container
        url = ""
        for a in container.find_all("a", href=True):
            href = a["href"]
            if "flussbad.com/event" in href or "rsvp" in a.get_text(strip=True).lower():
                url = href
                break

        key = (title, start_date.isoformat())
        if key in seen:
            continue
        seen.add(key)

        events.append(
            {
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "start_dt": start_dt,
                "end_dt": end_dt,
                "url": url,
            }
        )

    return events


def build_ics(events: list[dict]) -> str:
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//reethaus-ics//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Reethaus Program",
        "X-WR-TIMEZONE:Europe/Berlin",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
    ]
    lines.extend(VTIMEZONE.split("\n"))

    for ev in events:
        uid_src = f"{ev['title']}|{ev['start_date'].isoformat()}"
        uid = hashlib.sha1(uid_src.encode()).hexdigest()[:16] + "@reethaus-ics"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now}")
        lines.append(fold(f"SUMMARY:{ics_escape(ev['title'])}"))
        lines.append(
            fold("LOCATION:" + ics_escape("Reethaus, Köpenicker Chaussee 3a, 10317 Berlin"))
        )
        if ev["start_dt"]:
            lines.append(
                "DTSTART;TZID=Europe/Berlin:" + ev["start_dt"].strftime("%Y%m%dT%H%M%S")
            )
            lines.append(
                "DTEND;TZID=Europe/Berlin:" + ev["end_dt"].strftime("%Y%m%dT%H%M%S")
            )
        else:
            # All-day event (no time listed on the site)
            lines.append("DTSTART;VALUE=DATE:" + ev["start_date"].strftime("%Y%m%d"))
            lines.append(
                "DTEND;VALUE=DATE:"
                + (ev["end_date"] + timedelta(days=1)).strftime("%Y%m%d")
            )
        if ev["url"]:
            lines.append(fold(f"URL:{ics_escape(ev['url'])}"))
            lines.append(fold(f"DESCRIPTION:{ics_escape('Details / RSVP: ' + ev['url'])}"))
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    html = fetch_page()
    events = extract_events(html)

    if not events:
        # Never overwrite a working feed with an empty one — this most
        # likely means the site structure changed. Fail loudly instead.
        print("ERROR: no events found — page structure may have changed.", file=sys.stderr)
        return 1

    ics = build_ics(events)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ics)

    print(f"Wrote {OUTPUT_FILE} with {len(events)} events:")
    for ev in events:
        when = (
            ev["start_dt"].strftime("%d.%m.%Y %H:%M")
            if ev["start_dt"]
            else ev["start_date"].strftime("%d.%m.%Y (all day)")
        )
        print(f"  - {when}  {ev['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
