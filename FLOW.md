# Photo Booth — How It Actually Works

Follow this top to bottom. It covers everything: the stack, the files, every screen, every HTTP call, error handling, logging, and the inactivity system. Ask about anything.

---

## The Stack in One Sentence

A Python Flask server runs on the device (laptop for dev, Raspberry Pi in production). The customer sees a browser running fullscreen. Every action the customer takes in the browser sends an HTTP request to Flask, Flask runs the relevant Python module, and sends back a response.

```
Browser (index.html + app.js + inactivity.js)
        ↕  HTTP
Flask (main.py)
        ↕  function calls
Modules (camera.py, composer.py, reader.py, qr.py, log.py)
```

No database. No external services yet. Everything is local files and in-memory state.

---

## Project Structure

```
Photo_Booth/
├── .env                     ← All configuration. Change values here, not in code.
├── FLOW.md                  ← This file.
├── WHATS_NEXT.md            ← Roadmap and known gaps.
└── app/
    ├── main.py              ← Flask server. All HTTP routes live here.
    ├── modules/
    │   ├── camera.py        ← Captures frames from the camera
    │   ├── composer.py      ← Stitches photos into a strip image
    │   ├── reader.py        ← Listens for NFC card taps
    │   ├── qr.py            ← Generates QR codes
    │   └── log.py           ← Central logging setup (call log.get() everywhere)
    ├── templates/
    │   └── index.html       ← The entire UI (all 6 screens in one file)
    ├── static/
    │   ├── css/style.css    ← All visual styling
    │   └── js/
    │       ├── app.js       ← All frontend logic (screens, fetch calls, session state)
    │       └── inactivity.js ← Inactivity timeout logic (separate, loaded after app.js)
    ├── sessions/            ← Created automatically. One folder per customer session.
    │   └── {session_id}/
    │       ├── photo_1.jpg … photo_N.jpg
    │       └── strip.jpg
    └── logs/
        └── photobooth.log   ← Daily rotating log file, 30 days kept
```

> **sessions/** and **logs/** default to inside the app folder but can be overridden via `SESSIONS_DIR` and `LOGS_DIR` in `.env` — useful for pointing sessions at a USB drive on the Pi.

---

## Configuration (.env)

Every value that an operator might want to adjust lives in `.env`. Flask reads it at startup via `python-dotenv`. Python modules read from `os.environ`. JS values are injected into the HTML by Flask (Jinja2) so the browser can access them without exposing the file directly.

| Variable | Default | What it controls |
|---|---|---|
| `BOOTH_BASE_URL` | `http://localhost:5000` | Base URL encoded into QR codes |
| `INACTIVITY_TIMEOUT_SECS` | `300` | Seconds before steps/payment screens reset |
| `PROCESSING_RESET_SECS` | `60` | Seconds before processing screen auto-resets |
| `PHOTOS_PER_SESSION` | `4` | How many photos per session |
| `COUNTDOWN_SECS` | `3` | Countdown seconds before each shot |
| `PAYMENT_TIMEOUT_SECS` | `60` | How long payment screen waits for a tap |
| `SESSIONS_DIR` | `app/sessions` | Where photos and strips are stored |
| `LOGS_DIR` | `app/logs` | Where log files are written |
| `CAMERA_INDEX` | `0` | OpenCV device index |
| `PREVIEW_JPEG_QUALITY` | `75` | JPEG quality for live preview stream (0–100) |
| `STRIP_JPEG_QUALITY` | `92` | JPEG quality for saved strip (0–100) |
| `NFC_VENDOR_ID` | `0x1A86` | NFC reader USB vendor ID (hex) |
| `NFC_PRODUCT_ID` | `0xDD01` | NFC reader USB product ID (hex) |
| `FLASK_DEBUG` | `true` | Flask debug mode (set false in production) |
| `PAYMOB_API_KEY` | _(empty)_ | Paymob credentials (not wired up yet) |

---

## The 6 Screens

All 6 screens exist in `index.html` at all times. Only one has the CSS class `active` — the others are invisible (`opacity: 0`, `pointer-events: none`). The `goTo()` function in `app.js` swaps which one is active with a 400ms fade.

| # | ID | What it is |
|---|---|---|
| 1 | `screen-welcome` | Idle / attract screen |
| 2 | `screen-steps` | Explains the process + price |
| 3 | `screen-payment` | Card tap to pay |
| 4 | `screen-camera` | Live preview + countdown |
| 5 | `screen-processing` | Shows the finished strip + QR |
| 6 | `screen-error` | Handles all failures |

---

## The Full Flow

### 1. Welcome Screen

The booth sits here when idle. One button: **Let's Go** → calls `goToSteps()` in `app.js`.

`goToSteps()` resumes the inactivity timer and calls `goTo('screen-steps')`. Nothing happens on the server.

---

### 2. Steps Screen

Explains the process and shows the price. Button: **Press to Pay** → calls `goToPayment()`.

`goToPayment()`:
1. Resumes the inactivity timer (the customer is now in the flow — reset if they walk away)
2. Calls `goTo('screen-payment')`
3. After 700ms (letting the transition finish), calls `startPaymentFlow()`

---

### 3. Payment Screen

`startPaymentFlow()` makes a fetch call to `/payment/wait`.

**On the server**, that route calls `reader.wait_for_tap(timeout=PAYMENT_TIMEOUT_SECS)`.

`reader.py` runs a background thread that does one of two things depending on platform:

- **Windows (dev mode):** `_dev_loop()` puts a fake card UID into a queue every 3 seconds
- **Pi (production):** `_reader_loop()` opens the NFC reader directly by its USB IDs (read from `NFC_VENDOR_ID` / `NFC_PRODUCT_ID`) using `evdev`, reads raw key events, and assembles the card UID from keystrokes (the reader types the UID like a keyboard, then sends Enter)

`wait_for_tap()` drains any stale taps from previous sessions, then blocks on the queue until a tap arrives or the timeout elapses.

Back in the browser, `startPaymentFlow()` receives the response:
- **Success:** sets `paymentConfirmed = true`, shows "Approved!" briefly, calls `startCameraSession()`
- **Timeout (408):** shows "Timed out — tap again", retries automatically after 2s
- **Network error:** shows "Connection error — retrying", retries after 3s

> `paymentConfirmed` is a boolean in `app.js`. It starts `false` every session. The moment payment clears it becomes `true`. Every error after this point shows the session ID and "Run Diagnostics" instead of a simple retry — because the customer may have been charged.

---

### 4. Camera Screen

`startCameraSession()`:
1. Sets `paymentConfirmed = true`
2. Pauses the inactivity timer (the countdown is automated — no customer interaction expected)
3. Fetches `/new_session` — server generates a random 8-character session ID (e.g. `a3f20b1c`), creates no files yet, just returns the ID
4. Calls `goTo('screen-camera')`, then after 700ms calls `runCountdown()`

**The camera feed** is an `<img>` tag pointing at `/preview`. That route streams multipart JPEG frames (MJPEG). The browser renders it as a live video — no JavaScript required, just an image that keeps being replaced.

`camera.py` runs its own background thread:
- **Windows:** generates a dark placeholder frame with a pulsing green dot at ~30fps
- **Pi:** opens the camera via OpenCV (`CAMERA_INDEX` from env), sets 1280×720 MJPEG mode, warms up with 30 throwaway reads, then reads frames continuously into `_latest_frame` under a thread lock

`generate_preview()` reads `_latest_frame`, JPEG-encodes it at `PREVIEW_JPEG_QUALITY`, and yields it in the multipart format.

**The countdown loop** (`runCountdown()`) counts from `COUNTDOWN_SECS` down to 0 using `setInterval`. When it hits 0, it calls `triggerCapture()`.

`triggerCapture()`:
1. Flashes the screen white (CSS transition on a full-screen overlay div)
2. Shows "Got it!" text
3. Fetches `/capture/{session_id}/{photo_number}` — up to 3 retries with 800ms gap
4. Server calls `capture_photo()` which grabs `_latest_frame`, creates the session folder, and writes `photo_N.jpg`
5. If all retries fail → `showError()` with post-payment context
6. If success → increments `photosTaken`. If fewer than `PHOTOS_PER_SESSION`, restarts the countdown. At the last photo, calls `showStrip()`

---

### 5. Processing Screen

`showStrip()` navigates to `screen-processing` (inactivity timer stays paused — the machine is working, not the customer), then fetches `/compose/{session_id}`.

**On the server**, `compose()` in `composer.py`:
1. Opens all photos from the session folder using Pillow
2. Center-crops each one to 4:3 ratio
3. Resizes each to 840×630px
4. Creates a 900px-wide cream-coloured canvas
5. Pastes all photos vertically with gaps and a 2px sienna border around each
6. Draws a separator line, "photobooth" text, and the date at the bottom
7. Saves as `strip.jpg` at `STRIP_JPEG_QUALITY`

Back in the browser, once the strip image finishes loading (`img.onload`):
- The strip fades in
- `startProcessingCountdown()` begins — a visible "Resetting in Xs · Keep viewing" countdown
- `/qr/{session_id}` is fetched — Flask calls `qr.py` which generates a QR code encoding `{BOOTH_BASE_URL}/strip/{session_id}` and returns it as a PNG

**The processing countdown** counts down from `PROCESSING_RESET_SECS`. When it hits zero, `resetBooth()` fires. The customer can tap "Keep viewing" to restart it if they need more time to scan the QR.

> `BOOTH_BASE_URL` defaults to `http://localhost:5000`. On Pi with Cloudflare Tunnel it will be the public HTTPS URL so the QR works from the customer's phone.

---

### 6. Error Screen

`showError(title, message)` is called whenever something goes wrong. It checks `paymentConfirmed`:

**Pre-payment (`paymentConfirmed = false`):**
- Shows title + message
- One button: **Try Again** → calls `resetBooth()`

**Post-payment (`paymentConfirmed = true`):**
- Shows title + message
- Shows the session ID in large text (e.g. `A3F20B1C`) — "Please show this to our staff"
- Primary button: **Run Diagnostics** — placeholder for future automated recovery
- Secondary button: **Start Over** → calls `resetBooth()`

`resetBooth()` aborts any in-flight payment fetch, clears the processing countdown, pauses the inactivity timer, resets all session state, and returns to the welcome screen.

---

## Inactivity Timeout

Managed entirely by `inactivity.js`. The logic is an IIFE that exposes three methods: `pause()`, `resume()`, `reset()`.

The timer is **only active on the steps and payment screens** — the two places where a customer can abandon the flow and walk away. On all other screens it is paused.

| Screen | Timer state | Why |
|---|---|---|
| Welcome | Paused | Already the idle state |
| Steps | **Active** | Customer may walk away without paying |
| Payment | **Active** | Customer may abandon after seeing the price |
| Camera | Paused | Countdown is automated — no interaction expected |
| Processing | Paused | Machine is composing — not the customer's fault |
| Error | Paused | Customer must press a button to proceed |

Any `click`, `touchstart`, `mousemove`, or `keydown` resets the countdown. When it fires, `resetBooth()` is called — which also aborts the payment fetch if one is running.

The timeout value is `INACTIVITY_TIMEOUT_SECS` in `.env` (default 5 minutes).

---

## Logging

`log.py` sets up the root logger once using a `_configured` guard. Every module gets its own named logger via `log.get(__name__)`. All logs go to `LOGS_DIR/photobooth.log` and also print to the console.

Log files rotate at midnight, keeping 30 days of history.

| Event | Level |
|---|---|
| New session created | INFO |
| Card tapped (with UID) | INFO |
| Photo captured successfully | INFO |
| Strip composed | INFO |
| Camera opened successfully | INFO |
| NFC reader found | INFO |
| NFC reader not found | ERROR |
| evdev not installed | ERROR |
| Camera failed to open | ERROR |
| 10 consecutive camera read failures | WARNING |
| 50 consecutive camera read failures | ERROR |
| imwrite failed (disk full?) | ERROR |
| Compose failed (missing photos) | ERROR |
| QR generation failed | ERROR |
| Any unhandled Flask exception | ERROR + full traceback |
