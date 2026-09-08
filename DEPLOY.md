# New Pi Setup

Everything to do after flashing a fresh SD card. Follow in order.

---

## 1. Flash the SD Card

Use **Raspberry Pi Imager**.

- OS: Raspberry Pi OS Lite (64-bit)
- In settings (gear icon):
  - Hostname: `photobooth-1`
  - Username: `pbpi-1`
  - Password: (your password)
  - Enable SSH: yes
  - WiFi: add at least one network so it connects on first boot

---

## 2. Boot and SSH In

Find the Pi's IP on your router, or scan:
```bash
arp -a | findstr "dc-a6-32"
```

SSH in:
```bash
ssh pbpi-1@<pi-ip>
```

---

## 3. Install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the link it prints — log in with your Tailscale account. Once done, the Pi gets its permanent IP (`100.69.73.14`) and you can SSH from anywhere.

---

## 4. Add WiFi Networks

Add any cafe or venue networks the Pi needs to connect to:
```bash
sudo nmcli con add type wifi ifname wlan0 con-name "NetworkName" ssid "NetworkName" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "password"
```

See PI_SETUP.md for the full list of saved networks and passwords.

---

## 5. Install Python Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libopencv-dev
```

---

## 6. Clone the Repository

```bash
git clone https://github.com/kmb/photo-booth.git ~/photo-booth
```

When prompted for a password, use your **Personal Access Token** (not your GitHub password).

Save credentials so you don't have to enter them again:
```bash
git config --global credential.helper store
```

---

## 7. Install Python Packages

```bash
pip install -r ~/photo-booth/requirements.txt
```

---

## 8. Create the `.env` File

```bash
nano ~/photo-booth/.env
```

Copy the template below and fill in the values:

```
# Network
BOOTH_BASE_URL=http://localhost:5000

# Payment (Paymob)
PAYMOB_API_KEY=
PAYMOB_INTEGRATION_ID=
PAYMOB_IFRAME_ID=

# Kiosk behaviour
INACTIVITY_TIMEOUT_SECS=600
PROCESSING_RESET_SECS=60
PHOTOS_PER_SESSION=4
COUNTDOWN_SECS=10
PAYMENT_TIMEOUT_SECS=60

# Storage
SESSIONS_DIR=
LOGS_DIR=

# Camera
CAMERA_INDEX=0
PREVIEW_JPEG_QUALITY=75
PREVIEW_FPS=15
STRIP_JPEG_QUALITY=92

# NFC Reader
NFC_VENDOR_ID=0x1A86
NFC_PRODUCT_ID=0xDD01

# Pricing
CURRENCY=EGP
PRICE_1=150
PRICE_2=190
PRICE_3=220
PRICE_4=240

# Dev mode
PAYMENT_DEV_MODE=false

# Flask
FLASK_DEBUG=false
LOG_STDOUT=false
PYTHONUNBUFFERED=1
```

---

## 9. Create the systemd Service

```bash
sudo nano /etc/systemd/system/photobooth.service
```

Paste:
```ini
[Unit]
Description=Photobooth Kiosk
After=network.target

[Service]
User=pbpi-1
WorkingDirectory=/home/pbpi-1/photo-booth/app
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
EnvironmentFile=/home/pbpi-1/photo-booth/.env

[Install]
WantedBy=multi-user.target
```

Enable and start it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable photobooth
sudo systemctl start photobooth
sudo systemctl status photobooth
```

You should see `Active: active (running)`.

---

## 10. Verify

Open a browser on your laptop and go to:
```
http://<pi-ip>:5000
```

The booth should load. Check the logs if anything is wrong:
```bash
journalctl -u photobooth -f
```

---

## Done

The Pi is live. It will start the booth automatically on every boot.

For ongoing management, see **PI_SETUP.md** and **MAINTENANCE.md**.
