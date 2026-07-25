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

    theme = cfg.get("theme", "retro"); layout = cfg.get("wx_layout", "3day")
    def render(alert=None):
        return calendar_gen.generate(theme, lang, date=date, weather=weather,
                                     wx_layout=layout, now_dt=now_naive, alert=alert)

    # normal image
    with open("device.bin", "wb") as f:
        f.write(render())
    print("wrote device.bin")

    # alert variants — the whole bottom band becomes a warning card. The device
    # fetches one of these when it detects a condition. Add more here anytime
    # (free on the tier); the firmware picks which by measurement.
    L = lambda m: m.get(lang, m["en"])
    ALERTS = {
        "low": {"kind": "low",
                "title": L({"en": "Battery low", "zh": "電量偏低", "ja": "電池残量低下"}),
                "sub":   L({"en": "please charge soon", "zh": "請盡快充電", "ja": "充電してください"})},
        "critical": {"kind": "critical",
                "title": L({"en": "Battery critical", "zh": "電量過低", "ja": "電池残量わずか"}),
                "sub":   L({"en": "charge now", "zh": "請立即充電", "ja": "今すぐ充電"})},
    }
    for key, al in ALERTS.items():
        with open(f"device_{key}.bin", "wb") as f:
            f.write(render(alert=al))
        print(f"wrote device_{key}.bin")

if __name__ == "__main__":
    main()
