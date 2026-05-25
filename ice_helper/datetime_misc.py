from datetime import datetime, timezone


def ICE_ts_event_to_dt(ts_event: str) -> datetime:
    if ts_event:
        ts_event_micro = ts_event[:-4] + "Z" 
        ts_event_dt = datetime.strptime(ts_event_micro, "%Y-%m-%dT%H:%M:%S.%fZ")
        return ts_event_dt.replace(tzinfo=timezone.utc)
    raise ValueError('ts_event is None')