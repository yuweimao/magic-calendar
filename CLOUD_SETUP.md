# Magic Calendar — Cloud pull setup

Goal: the device updates itself daily with **no Mac and no phone** on. A free
GitHub Action renders `device.bin` once a day; the device wakes, downloads it,
shows it, and deep-sleeps.

```
GitHub Action (daily)  ->  device.bin in your repo  ->  device wakes, GETs it, displays, sleeps
```

Two parts: (1) put this folder in a GitHub repo and turn on the Action; (2) flash
the device with the pull firmware pointed at your repo.

---

## Part 1 — Cloud render (the always-on source)

**Files already prepared in this `magic/` folder:**
- `render_cloud.py` — renders today's image to `device.bin` (weather-aware, tz-correct)
- `.github/workflows/daily.yml` — runs `render_cloud.py` daily and commits `device.bin`
- `settings.json` — theme, language, weather toggle, your 粗坑里 location
- `calendar_gen.py`, `weather.py`, `fonts/` — the renderer

**Steps (once):**

1. Create a **new GitHub repo** (public is simplest so the device can fetch without auth).
   Name it e.g. `magic-calendar`.

2. Push this folder as the repo root. From Terminal:
   ```
   cd "$HOME/Desktop/Calendar sticker/magic"
   git init
   git add .
   git commit -m "Magic Calendar cloud render"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USER>/magic-calendar.git
   git push -u origin main
   ```

3. In the repo on GitHub: **Settings → Actions → General → Workflow permissions**
   → select **Read and write permissions** → Save.
   (Lets the Action commit the daily `device.bin`.)

4. Test the render now: repo **Actions** tab → **render-calendar** → **Run workflow**.
   After ~1 min it should commit a fresh `device.bin`. Open it — a new file appears/updates.

5. Your device image URL is:
   ```
   https://raw.githubusercontent.com/<YOUR_USER>/magic-calendar/main/device.bin
   ```
   Open it in a browser — it should download a 192000-byte file.

The Action is scheduled for **00:05 Asia/Taipei** (16:05 UTC). Change the `cron`
in `daily.yml` and `tz` in `settings.json` together if you move timezones.

> Note: GitHub may pause scheduled Actions on a repo with no pushes for ~60 days.
> The daily commit of `device.bin` counts as activity, so it keeps itself alive.

---

## Part 2 — Device pull firmware

1. Put your raw URL into the firmware. Edit
   `ESP8266_ePaperDisplay_MagicCalendar/src/main.cpp`, find `IMG_URL`, replace
   `USER/REPO`:
   ```c
   #define IMG_URL "https://raw.githubusercontent.com/<YOUR_USER>/magic-calendar/main/device.bin"
   ```

2. Flash the pull build (Ctrl-C the serial monitor first):
   ```
   cd "$HOME/Desktop/Calendar sticker/ESP8266_ePaperDisplay_MagicCalendar"
   ~/.platformio/penv/bin/pio run -e firebeetle32_pull -t upload
   ~/.platformio/penv/bin/pio device monitor -b 115200
   ```

3. First boot: it creates a WiFi hotspot **MagicCalendar** (same as before) if it
   has no saved network — join it and pick your WiFi once. After that it remembers.

4. Expected serial:
   ```
   Magic Calendar (pull) waking...
   WiFi ok, fetching https://raw.githubusercontent.com/.../device.bin
   fetched 192000 bytes
   Sent 192000 bytes in ~250 ms
   Refresh took ~30000 ms
   Panel refresh done.
   Deep sleep ~24h.
   ```
   The panel shows today's calendar, then the ESP32 deep-sleeps (~10 µA) until the
   next wake.

---

## Part 3 — Settings page (change what the calendar shows)

`settings.html` is a self-contained page. Serve it free from GitHub Pages so you
can open it on any phone or computer.

1. In the repo: **Settings → Pages → Build and deployment → Source: Deploy from a
   branch → Branch: `main` / `/root` → Save.** Wait ~1 min.

2. Your settings page is now at:
   ```
   https://<YOUR_USER>.github.io/magic-calendar/settings.html
   ```
   Bookmark it on your phone's home screen.

3. First time, open the **Connection** section and fill in:
   - GitHub user, repo (`magic-calendar`), branch (`main`)
   - A **fine-grained token**: GitHub → Settings → Developer settings →
     Fine-grained tokens → Generate. Scope it to just this repo, with
     **Contents: Read and write** (add **Actions: Read and write** to enable the
     “Save & apply now” button). The token is stored only in your browser.

4. Adjust theme / language / weather / location → **Save** (applies on the next
   daily render) or **Save & apply now** (renders immediately, ~1 min; then wake
   the device to pull it).

> The device never serves this page — it's asleep. Settings live in the repo's
> `settings.json`; the daily render reads them; the device just pulls the image.
> For a real consumer product you'd replace the pasted token with a GitHub login
> (OAuth) so users never see a token.

## How the pieces relate

- **Phone app** (future): edits `settings.json` in the repo (theme, language,
  weather on/off, location). Next daily render picks it up.
- **LAN preview** stays available: flash `-e firebeetle32` for the web-upload
  server when you want instant local tinkering; flash `-e firebeetle32_pull` for
  the hands-off battery mode.

## Known limitations / next tuning

- **Wake accuracy:** the 24h timer drifts a few seconds/day. For exact local-midnight
  wakes, add an NTP time sync after WiFi connects and compute sleep-to-next-00:10.
- **Panel deep sleep:** `epd.Sleep()` is disabled (it parks RST low and this board
  can't reliably wake the panel from it yet). The panel is bistable so it holds the
  image at ~0 power regardless; revisit once the RST wake path is solid.
- **TLS:** the firmware uses `setInsecure()` (no cert check) to fetch a public file.
  Fine for this; pin a root CA later if you want strict verification.
