import json, sys, urllib.request
from datetime import datetime, timezone

try:
    url = "https://api.openf1.org/v1/meetings?year=2026"
    resp = urllib.request.urlopen(url)
    meetings = json.loads(resp.read())
    now = datetime.now(timezone.utc)
    for m in sorted(meetings, key=lambda x: x.get("date_start", "")):
        start = datetime.fromisoformat(m.get("date_start", "").replace("Z", "+00:00"))
        end = datetime.fromisoformat(m.get("date_end", "").replace("Z", "+00:00"))
        h_until = (start - now).total_seconds() / 3600
        h_since = (now - end).total_seconds() / 3600
        if 0 <= h_until <= 48:
            print("Race in %.0fh" % h_until)
            sys.exit(0)
        if 0 <= h_since <= 24:
            print("Race ended %.0fh ago" % h_since)
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
