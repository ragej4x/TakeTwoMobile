from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

if ZoneInfo is not None:
    try:
        MANILA_TZ = ZoneInfo("Asia/Manila")
    except Exception:
        MANILA_TZ = timezone(timedelta(hours=8))
else:
    MANILA_TZ = timezone(timedelta(hours=8))


def now_manila() -> datetime:
    return datetime.now(MANILA_TZ)