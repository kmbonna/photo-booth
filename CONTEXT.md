# Project Context: Photo Booth

Rebuilt on 2026-11-15 from the repo, the docs, the architecture spec (.docx), local logs and git history. The aim is to let you (or a new Claude session) pick the project up without re-reading everything.

---

## 1. What the system is

A self-service photo booth kiosk. A Flask server runs on a Raspberry Pi 4, and the customer uses a single-page web UI in a browser. The customer picks how many copies they want and a filter ("mood"), taps a card on an NFC reader, gets 4 shots with a countdown before each one, and then sees a composed strip and a QR code that links to the digital copy.

### Architecture as built

```
Browser (templates/index.html + static/js/{poses,app,inactivity}.js)
     │  HTTP (fetch + an MJPEG <img src="/preview">)
     ▼
Flask  app/main.py  (dev server, 0.0.0.0:5000, threaded)
     │
     ├── modules/camera.py    background thread → _latest_frame (OpenCV V4L2, 1280×720 MJPG, mirrored)
     ├── modules/reader.py    background thread → queue of card UIDs (evdev HID keyboard; fake taps on Windows)
     ├── modules/composer.py  Pillow strip composition, per-mood palette and Polaroid borders
     ├── modules/moods.py     per-photo colour grading (noir, 70s)
     ├── modules/qr.py        QR PNG of {BOOTH_BASE_URL}/strip/{id}
     └── modules/log.py       root logger, daily rotation, 30 days kept, visitor/session fields
Disk: app/sessions/<8-hex-id>/photo_N.jpg + strip.jpg ; app/logs/photobooth.log
```

There is no database, no outbound network calls and no printing. All state is in memory or in local files.

### Routes (main.py)
| Route | Purpose |
|---|---|
| `GET /` | Renders the UI and injects the env values (timeouts, photo count, countdown, dev mode, currency, PRICE_1..4) |
| `POST /event` | Logs funnel events from the UI |
| `GET /camera/ready` | `true` once the camera thread has produced a frame |
| `GET /preview` | MJPEG stream. **This is what starts the camera thread** (lazy start) |
| `GET /payment/wait` | Blocks until an NFC tap or `PAYMENT_TIMEOUT_SECS`; returns 408 on timeout |
| `GET /new_session` | Returns `uuid4()[:8]` |
| `GET /capture/<sid>/<n>` | Saves the latest frame as photo_n.jpg |
| `GET /compose/<sid>?mood=` | Builds strip.jpg |
| `GET /qr/<sid>` | QR PNG |
| `GET /strip/<sid>` | Serves strip.jpg (the QR target) |

### UI flow (8 screens in index.html)
welcome → steps → **copies** → **mood** → payment → camera → processing → (error)

- On the welcome screen, `/camera/ready` is polled every 5 s. When the camera isn't ready, "Let's Go" is hidden and "Temporarily out of service" is shown.
- Payment: with `PAYMENT_DEV_MODE=true` a manual button appears. Otherwise `/payment/wait` is long-polled and retried on timeout.
- Camera: waits up to 10 s for camera readiness, then counts down with a random pose suggestion from poses.js before each shot. Each capture is retried 3 times.
- Processing: compose, show the strip and the QR code, then a `PROCESSING_RESET_SECS` auto-reset with a "Keep viewing" option.
- Errors after payment show the session ID and a "Run Diagnostics" button, which does nothing.

### Configuration
`main.py` loads `../.env` via python-dotenv. On the Pi, systemd also loads the same file through `EnvironmentFile`. Variables read by the code:

`BOOTH_BASE_URL, INACTIVITY_TIMEOUT_SECS, PROCESSING_RESET_SECS, PHOTOS_PER_SESSION, COUNTDOWN_SECS, PAYMENT_TIMEOUT_SECS, PAYMENT_DEV_MODE, CURRENCY, PRICE_1..PRICE_4, SESSIONS_DIR, LOGS_DIR, CAMERA_VENDOR_ID, CAMERA_PRODUCT_ID, CAMERA_INDEX, PREVIEW_FPS, PREVIEW_JPEG_QUALITY, STRIP_JPEG_QUALITY, NFC_VENDOR_ID, NFC_PRODUCT_ID, FLASK_DEBUG, LOG_STDOUT`

Present in `.env` but **not read by any code**: `PAYMOB_API_KEY, PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID` (all empty), `PYTHONUNBUFFERED` (read by Python itself, not by the app).

### Intended architecture (spec docx)
- Two repos: `photobooth-kiosk` (this repo) and `photobooth-central` (backend API, PostgreSQL with `booths`/`sessions`/`errors`, dashboard).
- Two independent systemd services on each Pi: `kiosk.service` and `health.service`. The health service is the only thing that talks to central (health every 30–60 s, plus syncing `session.json` files).
- Booth identity comes from config only: `BOOTH_ID`, `CENTRAL_API_URL`, `CENTRAL_API_TOKEN`.
- Development order: Core kiosk (incl. **printing**) → Payment → Reliability → Central → Monitoring → install.sh.
- Principles: local-first, simple, recoverable. Tailscale is for admin access only.
- The spec's proposed folder layout (`app/camera/`, `payment/`, `printing/`, `config/config.yaml`, `systemd/`, `scripts/`) isn't used. The repo has a flat `app/modules/` and `.env`. The spec says the layout "can evolve", so this isn't a violation, but `config.yaml` vs `.env` is an open decision (the `.env` approach matches the "tunables are env vars" rule).

---

## 2. Status

### Done and working (per code + logs)
- The full UI flow, including copies selection, mood selection, pose prompts, flash, countdown and inactivity reset.
- Camera on the Pi: auto-detection by USB VID:PID through `udevadm`, with `CAMERA_INDEX` as a fallback, and a self-healing loop (re-opens after 50 failed reads and retries opening every 5 s).
- Windows dev mode: a "NO CAMERA" placeholder and fake NFC taps every 3 s.
- Strip composition with three moods: default (cream, sienna frame), noir (B&W, grain, vignette, damaged silver Polaroid border) and 70s (Kodachrome cast, aged cream Polaroid border).
- QR generation and strip serving.
- Structured logging with visitor and session IDs and daily rotation.
- Camera check before payment (the welcome screen goes out-of-service when the camera isn't ready).
- systemd unit `photobooth.service`, Tailscale SSH (per the docs; not verified from here).

The last local session (2026-10-06, on Windows) completed a full noir session end to end.

### Half-built / stubs / dead code
| Item | State |
|---|---|
| **Payment** | Any NFC tap = approved. There is no Paymob code at all. The `PAYMOB_*` vars are unused. |
| **NFC reader** | Never tested on real hardware (WHATS_NEXT checkbox open). `evdev` isn't in requirements.txt. |
| **Printing** | Not started: no CUPS, no `/print` route. The README says "Strip prints automatically", which isn't true. |
| **Copies selection** | Only affects the displayed price. `selectedCopies` is never sent to the server, logged or used. |
| **Run Diagnostics** button | `onclick = null`, so it does nothing. |
| **Session metadata** | No `session.json` (copies, price, payment_status, session_status). The spec needs this for central sync. |
| **BOOTH_ID** | Not in `.env` or the code. |
| **health.service / central / install.sh** | Not started. |
| **Kiosk lock-down** | No fullscreen Chromium or auto-login. DEPLOY uses Pi OS **Lite** (no desktop), so the UI is currently viewed from another device's browser. |
| **Session cleanup** | Manual only. |
| `camera.stop()`, `reader.stop()` | Never called. |
| `main.py:18` comment | Says WARNING, but the level is set to INFO, so access logs are still written (polling `/camera/ready` every 5 s floods the log). |

### AI features (background swap, pose challenge)
**Neither appears anywhere**: not in WHATS_NEXT, the README, FLOW, the spec docx or the code. The closest existing pieces are the static pose suggestions in `poses.js` and the mood filters. If you want them:
- **Pose challenge**: a pose prompt plus on-device pose detection (e.g. MediaPipe Pose / MoveNet via TFLite) that scores the match or auto-triggers the shutter. A Pi 4 can manage roughly 5–15 fps with MoveNet Lightning. Run it on capture only, not on every preview frame, so the kiosk stays responsive (spec 26.9).
- **Background swap**: person segmentation (MediaPipe Selfie Segmentation, or rembg/U²-Net, which is much heavier) applied in `composer.py` per photo, with backgrounds as mood-like options. On a Pi 4, expect about 0.3–1 s per photo with MediaPipe and several seconds with rembg, which is a reason to keep it at compose time and to add the processing-screen mini-game idea.
- Both add heavy dependencies (spec 26.14: justify, and check aarch64 wheels). Per the spec's development order, they come **after** printing and payment.

---

## 3. Where the docs and the code disagree

| Doc | Says | Code / reality |
|---|---|---|
| DEPLOY §6 | `git clone https://github.com/kmb/photo-booth.git` | The remote is `https://github.com/kmbonna/photo-booth.git` |
| DEPLOY §5 + §7 | `apt install python3-opencv` **and** `pip install -r requirements.txt` (which pulls `opencv-python-headless`) | Two OpenCVs. On Pi OS Bookworm, a system-wide `pip install` fails with `externally-managed-environment` (PEP 668). |
| DEPLOY / requirements.txt | — | `evdev` is imported by reader.py but not listed anywhere. Without it, NFC fails (the error is logged and taps never arrive). |
| DEPLOY | Steps 9 → 11 | There is no step 10 |
| DEPLOY .env template | No `CAMERA_VENDOR_ID/PRODUCT_ID` | They're added separately in step 9. Easy to miss. |
| WHATS_NEXT | `kiosk.service` | DEPLOY and the other docs use `photobooth.service` (the spec also says `kiosk.service`). Pick one. |
| WHATS_NEXT | Mood Filters is a future idea with 6–7 moods | 3 moods are built (default, noir, 70s) |
| WHATS_NEXT | `PAYMENT_DEV_MODE` "auto-approve instantly" | It shows a manual approve button |
| WHATS_NEXT | `NFC_DEV_MODE`, `PRINTER_DEV_MODE` | Don't exist. NFC dev mode is tied to `sys.platform == "win32"`. |
| README | "Strip prints automatically", "Paymob integration" | Neither exists |
| README / DEPLOY / MAINTENANCE | Camera IDs "hex, no 0x" vs NFC IDs `0x1A86` | Both formats work for NFC (`int(x,16)`), but camera matching is a substring match, so `0x4c4a` would **fail** silently and fall back to the index |
| MAINTENANCE | Log at `logs/photobooth.log` / `~/photo-booth/logs/photobooth.log` | It's actually `~/photo-booth/app/logs/photobooth.log` (log.py: `modules/../logs`) |
| MAINTENANCE | `systemctl restart photobooth` (no sudo) | Needs `sudo` (PI_SETUP and README use sudo) |
| GIT_WORKFLOW | `ssh pi@<your-tunnel-hostname>` | `ssh pbpi-1@100.69.73.14` (Tailscale). GIT_WORKFLOW.md is also gitignored, so it isn't on the Pi or GitHub. |
| FLOW | "6 screens" | 8 (copies and mood were added) |
| FLOW | Windows placeholder "pulsing green dot ~30fps" | Static "NO CAMERA" frame at 10 fps |
| FLOW | Camera opened via `CAMERA_INDEX` | USB-ID resolution first, plus a recovery loop |
| FLOW | Composer: cream canvas plus sienna border only | Per-mood palettes, gradings and Polaroid borders |
| FLOW | `startCameraSession` immediately fetches `/new_session` | It first waits up to 10 s for `/camera/ready` |
| FLOW | Inactivity timer paused on welcome | `inactivity.js` starts it on page load (not paused). It fires `resetBooth()` on the welcome screen after the timeout. Harmless, but it logs noise. |
| FLOW | Config table | Missing `CAMERA_VENDOR_ID/PRODUCT_ID, PREVIEW_FPS, CURRENCY, PRICE_*, PAYMENT_DEV_MODE, LOG_STDOUT` |
| FLOW | Log line "Camera failed to open — check connection and CAMERA_INDEX" | Now "Camera failed to open at index N — retrying in 5s" (WARNING) |
| FLOW | "No external services yet… Cloudflare Tunnel" | Still true: `BOOTH_BASE_URL` is localhost, so the **QR doesn't work from a phone** |
| Spec | `config/config.yaml`, `systemd/` folder, `scripts/install.sh`, `health/` | None exist |
| `.claude/settings.local.json` | Paths under `/c/Users/LEGION/...` | From another machine. Harmless. |

---

## 4. Next steps

### From WHATS_NEXT, "Before Going Live" (open items)
1. Test the real NFC reader (VID/PID). Install `evdev` first.
2. Lock down as a kiosk: auto-login, fullscreen Chromium. This needs a desktop/X or Wayland on the Pi (Lite has neither) or a cage/labwc minimal compositor.
3. Add `BOOTH_ID` to `.env`.
4. Security and error sweep (see §5).
5. UI polish pass.
6. Domain + Cloudflare Tunnel → `BOOTH_BASE_URL` → test `/strip/<id>` from a phone.
7. Real payment: confirm what Paymob supports for self-service, wire up `/payment/wait`, test end to end.
8. Printing: choose a printer (dye-sub), CUPS, `/print/<sid>`, auto-print after compose, and honour `selectedCopies`.

Then the central system (health.service → photobooth-central → dashboard → install.sh), followed by the post-launch items (session cleanup cron, diagnostics, payment auth/capture).

### Missing from WHATS_NEXT but needed
- Send `copies` (and price) to the server and write `session.json` per session. Printing, the spec's sessions table and revenue tracking all depend on this.
- Add `evdev` to the dependency setup, and fix requirements.txt vs apt on Bookworm (decide: venv with `--system-site-packages` + pip, or apt-only).
- A `systemd/photobooth.service` file in the repo, so the unit isn't only in DEPLOY.md prose.
- A version marker, so you can see which commit the Pi is running (spec §21).
- A retry loop in reader.py when the NFC device isn't present at first use (see §5).
- AI features, if you still want them (see §2). They aren't recorded anywhere yet, so add them to WHATS_NEXT.

The spec's development order puts **printing** before payment. WHATS_NEXT lists payment first. Worth deciding.

---

## 5. Broken or risky

**High**
- **Werkzeug debugger exposed**: if `FLASK_DEBUG=true` on the Pi, the interactive debugger (remote code execution behind a PIN) is reachable on 0.0.0.0:5000 by anyone on the LAN or tailnet. The local `.env` has it `true`. Make sure the Pi's `.env` has `false`. The logs show "Debugger is active!" in many runs.
- **Payment accepts any tap**: any NFC card, or any keyboard device matching the VID:PID, starts a paid session. That's fine for testing, not for customers.
- **No auth on any route**: anyone who can reach port 5000 can call `/capture`, `/compose` and `/strip/<id>`, and every customer strip ever taken is downloadable by ID (8 hex chars, never expires, never deleted).
- **The QR code is useless** until `BOOTH_BASE_URL` is a URL that phones can reach.

**Medium**
- **NFC thread dies permanently**: if the reader isn't found the first time `/payment/wait` is called, `_reader_loop` returns but `_running` stays True. Taps never work until the service restarts, and the UI just loops "Timed out — tap again". The same happens on disconnect.
- **NFC permissions**: reading `/dev/input/event*` requires the service user to be in the `input` group. This isn't in DEPLOY.
- **NFC reader not grabbed** (`device.grab()`): once Chromium runs on the Pi, the UID keystrokes and Enter also go to the focused page and can press the focused button.
- **Stale-frame capture**: `capture_photo` takes `_latest_frame` with no timestamp check. If the camera freezes, it silently saves an old frame and the user sees a duplicated photo.
- **Camera starts only when `/preview` is first requested** (lazy `start()`). If nothing loads `/` (and so the `<img src=/preview>`), `/camera/ready` is false forever. Once a browser is open, the stream runs continuously at `PREVIEW_FPS` even on hidden screens, which costs CPU and WiFi all the time, and every extra browser tab adds another encoder loop.
- **`_resolve_camera_index`** runs `sorted(glob('/dev/video*'))`, which is lexical (video10 before video2). It also substring-matches the whole udevadm dump, so a short ID could false-match. Fine for the current single camera.
- **Fonts**: composer falls back to `ImageFont.load_default()` if DejaVu/Liberation are missing. On Pillow older than 10.1 that bitmap font doesn't support `anchor='mt'`, so compose raises an exception. Make sure `fonts-dejavu-core` is installed on the Pi.
- **Dependency drift**: requirements.txt is fully unpinned. pip and apt OpenCV conflict.
- **Disk**: sessions are never cleaned. Each session is about 1–2 MB, so the SD card fills over months.
- **Error handler** returns `str(e)` to the client.
- **Flask dev server in production**: acceptable for one kiosk, but it isn't designed for it.

**Low**
- Inactivity timer runs on the welcome screen (log noise).
- Werkzeug access logs at INFO, with `/camera/ready` every 5 s per open browser, which bloats the logs.
- The session ID `..` reaches `os.path.join` (Flask blocks `/` in path segments, so the impact is limited to `app/` files named photo_N.jpg/strip.jpg). Still worth validating IDs against `^[0-9a-f]{8}$`.
- `sessions/` has 27 local test sessions (gitignored, so there's nothing to fix).
