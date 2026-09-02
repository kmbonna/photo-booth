# What's Next

---

## Product Ideas

Things that would make the booth more interesting or profitable. None of these are blockers — they're additions for after the first version is live.

### Mood Filters
Let the customer pick a look before the countdown starts. Add a new screen between payment and camera with 5–6 options. Each mood is a Pillow colour matrix applied to every photo before stitching.

Suggested moods:
- **Normal** — no processing
- **Vintage** — sepia tint, soft vignette, faded blacks
- **Noir** — full desaturation, high contrast
- **70s** — warm orange-brown cast, faded blacks
- **Early 2000s** — slight overexposure, cyan shadows
- **Gritty** — heavy grain, crushed blacks
- **High Flash** - High Flash

Implementation lives entirely in `composer.py` (Pillow LUT / colour matrix). The new screen is pure HTML/JS — no backend changes beyond passing the selected mood to `/compose`.

### Seasonal Strip Decorations
Swap the strip border, footer branding, and background palette based on the time of year. Could be calendar-driven (auto-switch on dates) or toggled via an env variable for manual control.

Examples: fairy lights + snow for winter, flowers + pastels for spring, warm grain for autumn. Pillow already handles the strip layout — just swap assets and colour tokens in `composer.py`.

### Processing Screen Mini-Game
A small distraction while the strip is composing (takes a few seconds on Pi). Ideas:
- A tap-the-frame reflex game
- A "guess the filter" quiz tied to the selected mood
- A looping film-reel animation with photography trivia

Pure JS/CSS — no server round-trips, no libraries. Hidden once `img.onload` fires.

### Granular Dev Mode Flags
Currently dev mode is all-or-nothing — `sys.platform == "win32"` switches camera and NFC to fake versions simultaneously. Replace this with independent env var toggles so each hardware component can be faked separately:

```
CAMERA_DEV_MODE=true     # fake frames instead of real camera
NFC_DEV_MODE=true        # auto-fire a fake card tap every 3s
PAYMENT_DEV_MODE=true    # skip Paymob, auto-approve instantly
PRINTER_DEV_MODE=true    # log "would print" instead of sending to CUPS
```

This lets you mix and match — e.g. test a new filter with a real camera but fake payment, or test the payment flow with a real NFC reader but fake camera. Build this when you have a second component to test independently (e.g. once the printer is added).

---

## Before Going Live

Everything in this section needs to be done before the first paying customer.

### Raspberry Pi Setup
- [ ] Flash SD card and boot Pi headless
- [ ] Install Python dependencies (OpenCV, evdev, Pillow, Flask, python-dotenv, qrcode)
- [ ] Test real camera — adjust `CAMERA_INDEX` in `.env` if needed
- [ ] Test real NFC reader — confirm `NFC_VENDOR_ID` / `NFC_PRODUCT_ID` match the device
- [ ] Set up systemd service so Flask auto-starts on boot and restarts on crash
- [ ] Lock down as a kiosk (disable keyboard shortcuts, auto-login, fullscreen Chromium)

### Remote Access (Cloudflare SSH Tunnel)
Do this while you still have physical access — after this you can manage the booth from anywhere.
- [ ] Install `cloudflared` on the Pi
- [ ] Authenticate with your Cloudflare account (`cloudflared tunnel login`)
- [ ] Create a tunnel and add an SSH hostname to your Cloudflare DNS
- [ ] Run the tunnel as a second systemd service alongside Flask
- [ ] Test SSH access from your laptop over the tunnel
- [ ] Read `MAINTENANCE.md` — covers the common commands you'll need remotely

> This runs on the same Pi as the booth. No extra hardware needed.

### Public URL (QR Codes)
- [ ] Set up Cloudflare Tunnel on Pi
- [ ] Set `BOOTH_BASE_URL` in `.env` to the public HTTPS tunnel URL
- [ ] Test that `/strip/{session_id}` is reachable from a phone on any network

### Real Payment
- [ ] Confirm Paymob supports payment via QR / InstaPay webhook for self-service
- [ ] Fill in `PAYMOB_API_KEY`, `PAYMOB_INTEGRATION_ID`, `PAYMOB_IFRAME_ID` in `.env`
- [ ] Wire up payment verification in `/payment/wait` (currently accepts any card tap)
- [ ] Test end-to-end: real card → Paymob webhook → booth continues

### Printing
- [ ] Choose printer (dye-sub recommended — Canon Selphy, DNP, Mitsubishi)
- [ ] Install CUPS on Pi and add printer
- [ ] Add `/print/{session_id}` Flask route that sends `strip.jpg` to CUPS
- [ ] Trigger print automatically after compose, or add a button on the processing screen

---

## After Going Live

Build these once real sessions are running and real logs exist. Don't guess — let the logs tell you what actually breaks.

### Session Cleanup
Old session folders accumulate on disk. Add a cron job on the Pi that deletes sessions older than 24h. One line of Python or a simple shell script.

### Run Diagnostics (post-payment error recovery)
Currently the "Run Diagnostics" button on the post-payment error screen is a placeholder. Eventually:
- Build `/diagnostics/{session_id}` — checks camera alive, photos on disk, strip composable, QR generatable
- Show a live checklist on the error screen as each check runs
- Auto-recover where possible (retry compose, retry QR) and proceed automatically if fixed
- If unrecoverable, show exactly what failed so the customer can describe it

Wait for real logs before building this — no point guessing which failures actually happen.

### Payment Auth + Capture
Currently payment is all-or-nothing. Better flow:
- Authorise the card on tap (money reserved, not taken)
- Capture only after strip is composed and printed successfully
- Void the auth automatically if anything fails post-payment (customer charged nothing)

Requires Paymob to support auth/capture separately — confirm with their API docs before building.

---

## Known Gaps

Edge cases that aren't handled yet. Low priority until the booth is live and you know which ones actually happen.

- No auto-retry if the camera preview freezes mid-session
- No reconnection detection if the network drops between fetches
- No disk-full warning before it actually fails (imwrite will fail silently-ish)
- If Flask crashes entirely — black screen, no recovery until systemd restarts it
- If Pi loses power mid-session — session folder stays on disk but the customer loses their strip
