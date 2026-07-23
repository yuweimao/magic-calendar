#!/usr/bin/env python3
"""Generate today's calendar image and push it to the device over WiFi.

Reads settings.json for location, language, theme, and whether the bottom band
shows a quote or the weather. When bottom == "weather", fetches the forecast
(CWA township primary, Open-Meteo fallback) and renders it into the image.

Usage:
  python3 push_today.py --ip 192.168.1.134
  python3 push_today.py --ip 192.168.1.134 --bottom quote     # override to quote
Options override settings.json when given.
"""
import argparse, os, subprocess, tempfile, datetime, sys, json
import calendar_gen
import weather as wx

def main():
    cfg = {}
    if os.path.exists("settings.json"):
        cfg = json.load(open("settings.json"))

    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", required=True, help="device IP, e.g. 192.168.1.134")
    ap.add_argument("--theme", default=cfg.get("theme","retro"),
                    choices=["minimal","retro","mono","dots","diy"])
    ap.add_argument("--lang",  default=cfg.get("lang","zh"), choices=["zh","en","ja"])
    ap.add_argument("--bottom", default=cfg.get("bottom","quote"),
                    choices=["quote","weather"])
    ap.add_argument("--wx-layout", default=cfg.get("wx_layout","3day"),
                    choices=["3day","today"])
    a = ap.parse_args()

    weather = None
    if a.bottom == "weather":
        weather = wx.get_forecast(cfg, a.lang)
        if weather is None:
            print("weather fetch failed -> showing quote instead")
    print("weather source:", weather["source"] if weather else "(quote)")

    data = calendar_gen.generate(a.theme, a.lang, weather=weather, wx_layout=a.wx_layout)
    binp = os.path.join(tempfile.gettempdir(), "cal_today.bin")
    open(binp, "wb").write(data)

    url = f"http://{a.ip}/upload"
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] pushing {a.theme}/{a.lang}/{a.bottom} -> {url}")
    r = subprocess.run(["curl","-s","-S","--max-time","90","-F",f"image=@{binp}",url],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("curl error:", r.stderr.strip()); sys.exit(1)
    print("device:", r.stdout.strip() or "(uploaded)")

if __name__ == "__main__":
    main()
