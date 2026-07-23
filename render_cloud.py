#!/usr/bin/env python3
"""Cloud render entry point (runs in GitHub Actions, once a day).

Renders today's calendar image straight to device.bin using settings.json.
Timezone-correct: the date and golden-hour sky use the configured local tz,
not the runner's UTC clock. The device downloads this file and displays it.
No network push here -- the workflow commits device.bin; the device pulls it.
"""
import json, datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
import calendar_gen
import weather as wx

def main():
    cfg = json.load(open("settings.json"))
    lang = cfg.get("lang", "zh")

    tz = None
    if ZoneInfo:
        try: tz = ZoneInfo(cfg.get("tz", "Asia/Taipei"))
        except Exception: tz = None
    now = datetime.datetime.now(tz) if tz else datetime.datetime.now()
    date = now.date()
    now_naive = now.replace(tzinfo=None)

    weather = None
    if cfg.get("bottom", "quote") == "weather":
        weather = wx.get_forecast(cfg, lang)
        if weather is None:
            print("weather fetch failed -> rendering quote instead")
    print("date:", date, "| weather source:", weather["source"] if weather else "(quote)")

    data = calendar_gen.generate(cfg.get("theme", "retro"), lang, date=date,
                                 weather=weather, wx_layout=cfg.get("wx_layout", "3day"),
                                 now_dt=now_naive)
    with open("device.bin", "wb") as f:
        f.write(data)
    print(f"wrote device.bin ({len(data)} bytes)")

if __name__ == "__main__":
    main()
