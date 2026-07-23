#!/usr/bin/env python3
"""Daily weather for the Magic Calendar.

Primary source: CWA 中央氣象署 township forecast (needs a free Authorization key).
Fallback:       Open-Meteo (no key, global, ~1-11 km grid).

Runs wherever the render runs (your Mac via push_today, or the cloud job) -- NOT on
the battery device. Returns a plain dict the renderer draws into the bottom band:

    {
      "loc": "粗坑里",
      "now": 31, "hi": 33, "lo": 26,          # deg C, ints
      "kind": "partly", "cond": "多雲時晴",     # icon key + localized text
      "rain": 20, "sunrise": "05:18", "sunset": "18:42",
      "days": [ {"wd":"今天","kind":"partly","hi":33,"lo":26},
                {"wd":"週五","kind":"rain","hi":30,"lo":25},
                {"wd":"週六","kind":"sunny","hi":34,"lo":27} ],
      "source": "cwa" | "open-meteo" | "sample",
    }

If every network path fails, get_forecast() returns None so the renderer can fall
back to the quote instead of showing stale/blank weather.
"""
import json, datetime, urllib.request, urllib.parse, ssl

# macOS python.org builds often ship without a CA bundle -> SSL verify fails.
# Prefer certifi's bundle; if verification still fails, fall back to unverified
# (weather data only, low risk) so the calendar never blanks over a cert issue.
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

# ---- WMO weather_code -> (icon kind, zh, en, ja) -------------------------------
WMO = {
    0:("sunny","晴","Clear","晴"),
    1:("partly","晴時多雲","Mostly Clear","晴時々曇"),
    2:("partly","多雲","Partly Cloudy","くもり"),
    3:("cloudy","陰","Overcast","くもり"),
    45:("cloudy","有霧","Fog","霧"), 48:("cloudy","霧","Rime Fog","霧"),
    51:("rain","毛毛雨","Drizzle","霧雨"), 53:("rain","毛毛雨","Drizzle","霧雨"),
    55:("rain","毛毛雨","Drizzle","霧雨"),
    61:("rain","小雨","Light Rain","小雨"), 63:("rain","降雨","Rain","雨"),
    65:("rain","大雨","Heavy Rain","大雨"),
    71:("cloudy","小雪","Light Snow","雪"), 73:("cloudy","雪","Snow","雪"),
    75:("cloudy","大雪","Heavy Snow","大雪"),
    80:("rain","陣雨","Showers","にわか雨"), 81:("rain","陣雨","Showers","にわか雨"),
    82:("rain","強陣雨","Heavy Showers","激しい雨"),
    95:("storm","雷雨","Thunderstorm","雷雨"), 96:("storm","雷雨","Thunderstorm","雷雨"),
    99:("storm","雷雨","Thunderstorm","雷雨"),
}
def _wmo(code, lang):
    kind, zh, en, ja = WMO.get(int(code), ("cloudy","--","--","--"))
    return kind, {"zh":zh,"en":en,"ja":ja}[lang]

_WD = {"zh":["週一","週二","週三","週四","週五","週六","週日"],
       "en":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
       "ja":["月","火","水","木","金","土","日"]}
def _wd(date, lang, i):
    return "今天" if (i==0 and lang=="zh") else ("Today" if (i==0 and lang=="en") else
           ("今日" if (i==0 and lang=="ja") else _WD[lang][date.weekday()]))

def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent":"MagicCalendar/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return json.load(r)
    except ssl.SSLCertVerificationError:
        # last resort so a missing CA bundle can't blank the calendar
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl._create_unverified_context()) as r:
            return json.load(r)

# ---- Open-Meteo (no key) -------------------------------------------------------
def open_meteo(lat, lon, lang="zh", tz="Asia/Taipei", loc=""):
    url = ("https://api.open-meteo.com/v1/forecast?"
           + urllib.parse.urlencode({
               "latitude": lat, "longitude": lon,
               "current": "temperature_2m,weather_code",
               "daily": "temperature_2m_max,temperature_2m_min,weather_code,"
                        "precipitation_probability_max,sunrise,sunset",
               "timezone": tz, "forecast_days": 3}))
    j = _get(url)
    cur, day = j["current"], j["daily"]
    today = datetime.date.fromisoformat(day["time"][0])
    kind, cond = _wmo(cur["weather_code"], lang)
    days = []
    for i in range(min(3, len(day["time"]))):
        d = datetime.date.fromisoformat(day["time"][i])
        k, _ = _wmo(day["weather_code"][i], lang)
        days.append({"wd": _wd(d, lang, i), "kind": k,
                     "hi": round(day["temperature_2m_max"][i]),
                     "lo": round(day["temperature_2m_min"][i])})
    return {"loc": loc, "now": round(cur["temperature_2m"]),
            "hi": days[0]["hi"], "lo": days[0]["lo"],
            "kind": kind, "cond": cond,
            "rain": int(day["precipitation_probability_max"][0] or 0),
            "sunrise": day["sunrise"][0][-5:], "sunset": day["sunset"][0][-5:],
            "days": days, "source": "open-meteo"}

# ---- CWA township (needs free key) ---------------------------------------------
# Dataset F-D0047-093 = all-Taiwan township 3-day forecast; filter by district.
# CWA 'Wx' element carries a weather description + a numeric code we map via WMO-ish.
def cwa(district, key, lang="zh", loc=""):
    url = ("https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-093?"
           + urllib.parse.urlencode({"Authorization": key, "locationName": district,
                                     "elementName": "T,MaxT,MinT,Wx,PoP12h"}))
    j = _get(url)
    locs = j["records"]["locations"][0]["location"]
    if not locs:
        raise ValueError(f"CWA: district '{district}' not found")
    elems = {e["elementName"]: e["time"] for e in locs[0]["weatherElement"]}
    def val(name, idx=0):
        return elems[name][idx]["elementValue"][0]["value"]
    # CWA 'Wx' value[1] is a weather code (1..41); map coarse buckets to our icons.
    def wx_kind(code):
        c = int(code)
        if c in (1,): return "sunny", val_wx_text(0)
        if c in (2,3,4): return "partly", val_wx_text(0)
        if c in (5,6,7,8,9,10,11,12,13): return "cloudy", val_wx_text(0)
        if c in (19,20,21,22,23,24,25,26,27,28,29): return "rain", val_wx_text(0)
        if c in (15,16,17,18,33,34,35,36,37,38,39,41): return "storm", val_wx_text(0)
        return "cloudy", val_wx_text(0)
    def val_wx_text(idx):
        return elems["Wx"][idx]["elementValue"][0]["value"]
    wx_code = elems["Wx"][0]["elementValue"][1]["value"]
    kind, cond = wx_kind(wx_code)
    days = []
    n = min(3, len(elems["MaxT"]))
    for i in range(n):
        d = datetime.date.fromisoformat(elems["MaxT"][i]["startTime"][:10])
        kc = elems["Wx"][i]["elementValue"][1]["value"]
        k, _ = wx_kind(kc)
        days.append({"wd": _wd(d, lang, i), "kind": k,
                     "hi": int(elems["MaxT"][i]["elementValue"][0]["value"]),
                     "lo": int(elems["MinT"][i]["elementValue"][0]["value"])})
    return {"loc": loc or district, "now": int(val("T")),
            "hi": days[0]["hi"], "lo": days[0]["lo"], "kind": kind, "cond": cond,
            "rain": int(val("PoP12h") or 0), "sunrise": "", "sunset": "",
            "days": days, "source": "cwa"}

# ---- public entry: try CWA, then Open-Meteo, then give up ----------------------
def get_forecast(cfg, lang="zh"):
    """cfg keys: loc, lat, lon, district, cwa_key (optional), tz."""
    loc = cfg.get("loc","")
    # 1) CWA if we have a key + Taiwan district
    if cfg.get("cwa_key") and cfg.get("district"):
        try:
            return cwa(cfg["district"], cfg["cwa_key"], lang, loc)
        except Exception as e:
            print("CWA failed, falling back to Open-Meteo:", e)
    # 2) Open-Meteo
    try:
        return open_meteo(cfg["lat"], cfg["lon"], lang, cfg.get("tz","Asia/Taipei"), loc)
    except Exception as e:
        print("Open-Meteo failed:", e)
        return None

# ---- offline sample (for rendering without network) ----------------------------
def sample(loc="粗坑里", lang="zh"):
    return {"loc": loc, "now": 31, "hi": 33, "lo": 26, "kind": "partly",
            "cond": "多雲時晴" if lang=="zh" else "Partly Cloudy",
            "rain": 20, "sunrise": "05:18", "sunset": "18:42",
            "days": [{"wd":_wd(datetime.date.today(),lang,0),"kind":"partly","hi":33,"lo":26},
                     {"wd":"週五","kind":"rain","hi":30,"lo":25},
                     {"wd":"週六","kind":"sunny","hi":34,"lo":27}],
            "source": "sample"}

if __name__ == "__main__":
    import sys
    cfg = json.load(open("settings.json"))
    fc = get_forecast(cfg, cfg.get("lang","zh")) or sample()
    print(json.dumps(fc, ensure_ascii=False, indent=2))
