#!/usr/bin/env python3
"""
Compare the previous and current reethaus.ics and print newly added events,
one per line, formatted for a notification. Prints nothing if no new events.

Usage: python new_events.py old.ics reethaus.ics
"""

import re
import sys


def parse_events(path: str) -> dict[str, str]:
    """Return {UID: human-readable description} for each VEVENT."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {}

    # Unfold RFC 5545 folded lines
    text = text.replace("\r\n ", "").replace("\n ", "")

    events = {}
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        uid = re.search(r"UID:(\S+)", block)
        summary = re.search(r"SUMMARY:(.+)", block)
        dtstart = re.search(r"DTSTART[^:]*:(\S+)", block)
        if not uid:
            continue
        title = summary.group(1).strip() if summary else "(untitled)"
        title = title.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")
        when = ""
        if dtstart:
            raw = dtstart.group(1)
            m = re.match(r"(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2}))?", raw)
            if m:
                y, mo, d, hh, mm = m.groups()
                when = f"{d}.{mo}.{y}"
                if hh:
                    when += f" {hh}:{mm}"
        events[uid.group(1)] = f"{when}  {title}".strip()
    return events


def main() -> int:
    old_path, new_path = sys.argv[1], sys.argv[2]
    old = parse_events(old_path)
    new = parse_events(new_path)

    # An empty old feed means first run — don't announce everything as new
    if not old:
        return 0

    added = [desc for uid, desc in new.items() if uid not in old]
    for line in sorted(added):
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    main()
