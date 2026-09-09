# Photo Booth

A self-service photo booth kiosk built on a Raspberry Pi. Customers choose a filter, tap to pay, shoot 4 photos, and walk away with a printed strip and a QR code to their digital copy.

## How it works

1. Customer taps **Let's Go** on the welcome screen
2. Selects number of copies and a mood filter (Default, Noir, 70s)
3. Taps their card on the NFC reader to pay
4. 4 photos are taken with a countdown between each
5. Strip is composed and displayed — customer scans the QR code for their digital copy
6. Strip prints automatically

## Stack

- **Backend**: Python / Flask
- **Camera**: OpenCV (V4L2), USB webcam auto-detected by vendor/product ID
- **Image processing**: Pillow + NumPy (filters, strip composition, Polaroid borders)
- **Frontend**: Vanilla JS, MJPEG live preview stream
- **Payment**: NFC card reader (Paymob integration)
- **Deployment**: Raspberry Pi 4, systemd service, Tailscale for remote access

## Filters

| Mood | Photo grade | Strip |
|---|---|---|
| Default | None | Warm cream, thin accent frame |
| Noir | B&W, high contrast, heavy grain + vignette | Near-black background, worn Polaroid border |
| 70s | Kodachrome warm cast, soft grain + vignette | Amber background, aged Polaroid border |

## Project structure

```
app/
  main.py              # Flask routes
  modules/
    camera.py          # Camera thread, auto-detection, self-healing recovery loop
    composer.py        # Strip composition, per-mood borders and palettes
    moods.py           # Pixel-level filter processing
    reader.py          # NFC reader
    qr.py              # QR code generation
    log.py             # Structured logging
  templates/
    index.html         # Single-page kiosk UI
  static/
    css/style.css
    js/app.js          # Flow logic, camera session, payment
    js/poses.js        # Pose suggestions shown during countdown
    js/inactivity.js   # Inactivity timer
```

## Environment variables

All tunables live in `.env` — see the template in `DEPLOY.md`. Key ones:

| Variable | Description |
|---|---|
| `CAMERA_VENDOR_ID` / `CAMERA_PRODUCT_ID` | USB IDs for auto-detection (hex, no 0x) |
| `PREVIEW_FPS` | Live preview frame rate cap |
| `PRICE_1..4` | Price per copy count in EGP |
| `CURRENCY` | Currency label shown on screen |
| `COUNTDOWN_SECS` | Countdown seconds before each shot |
| `PAYMENT_DEV_MODE` | Show manual approve button instead of NFC |

## Setup

Fresh Pi setup: follow **DEPLOY.md** step by step.

Ongoing Pi management: see **PI_SETUP.md**.

Updating after a code change:
```bash
cd ~/photo-booth && git pull
sudo systemctl restart photobooth
```

## Docs

- `DEPLOY.md` — fresh Pi flash setup
- `PI_SETUP.md` — ongoing management, WiFi, systemd, logs
- `MAINTENANCE.md` — day-to-day operations
- `WHATS_NEXT.md` — roadmap
