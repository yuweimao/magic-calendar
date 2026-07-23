# Magic Calendar — automation

Generate today's calendar image and push it to the device automatically each day.

```
magic/
  fonts/            bundled fonts (so it runs anywhere, identically)
  calendar_gen.py   the renderer  -> packed 800x480 7-color image (192000 bytes)
  push_today.py     render today + upload to the device over WiFi
```

## 1. One-time setup (on the Mac)

```
cd "~/Desktop/Calendar sticker/magic"
python3 -m pip install --user pillow numpy
```

Find your device's IP from the serial monitor (the `http://192.168.x.x` line), or your router.

## 2. Test it

```
python3 push_today.py --ip 192.168.1.134
```
The panel should refresh to today's date. Theme, language, weather toggle, and
location all come from `settings.json`. Flags override it for a one-off:
- `--theme` minimal | retro | mono | dots | diy
- `--lang`  zh | en | ja
- `--bottom` quote | weather        (weather uses your settings.json location)
- `--wx-layout` 3day | today

## 3. Run it automatically every day

The device updates itself if this runs once a day. Two ways on macOS:

### Easiest: cron
```
crontab -e
```
Add (runs daily at 00:05; use the path that `which python3` prints):
```
5 0 * * * cd "$HOME/Desktop/Calendar sticker/magic" && /usr/bin/python3 push_today.py --ip 192.168.1.134 >> push.log 2>&1
```

### Or launchd (survives reboots cleanly)
Save as `~/Library/LaunchAgents/com.magic.calendar.plist`, then
`launchctl load ~/Library/LaunchAgents/com.magic.calendar.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.magic.calendar</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>push_today.py</string>
    <string>--ip</string><string>192.168.1.134</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/yuweimao/Desktop/Calendar sticker/magic</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>5</integer></dict>
  <key>StandardOutPath</key><string>/tmp/magic-calendar.log</string>
  <key>StandardErrorPath</key><string>/tmp/magic-calendar.err</string>
</dict></plist>
```

## How it works / limitations
- **Push model:** the Mac generates the image and uploads it to the device's `/upload`.
- Requires the **Mac to be awake** at the scheduled time and the **device powered + on WiFi**.
- This is the prototype path. For the battery/solar version we'll switch to a **pull model**:
  the device wakes once a day, fetches its image, displays it, and deep-sleeps — so it no longer
  depends on the Mac. (That needs the firmware deep-sleep work + an always-on place to run the
  generator, e.g. a Raspberry Pi or a tiny cloud function. The same `calendar_gen.py` runs there.)
```
