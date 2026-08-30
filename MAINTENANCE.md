# Maintenance Guide

How to manage the booth remotely after it's live. Everything here assumes you've set up a Cloudflare SSH tunnel on the Pi (see WHATS_NEXT.md → Remote Access).

---

## Getting In

```bash
ssh pi@your-tunnel-hostname
```

That's it. Works from any network, anywhere. No VPN, no port forwarding.

Once in, you're on the Pi. The booth code lives at:
```bash
cd ~/Photo_Booth
```

---

## The Two Things Running

Two systemd services run on the Pi at all times:

| Service | What it is |
|---|---|
| `photobooth` | Your Flask app — the booth itself |
| `cloudflared` | The Cloudflare tunnel — your remote access |

Check both are alive:
```bash
systemctl status photobooth
systemctl status cloudflared
```

---

## Checking Logs

**App logs** — card taps, session IDs, errors, everything your code logs:
```bash
# Live tail on Pi
tail -f logs/photobooth.log

# Live tail on Windows (run in a second Anaconda prompt)
powershell Get-Content -Path app\logs\photobooth.log -Wait -Tail 20
```
```bash
# More log commands:

# Last 100 lines
tail -100 logs/photobooth.log

# Search for errors only
grep ERROR logs/photobooth.log

# Search for a specific session
grep a3f20b1c logs/photobooth.log
```

**System logs** — Flask startup, crashes, anything before the app was running:
```bash
# Live tail
journalctl -u photobooth -f

# Last 50 lines
journalctl -u photobooth -n 50

# Everything since last boot
journalctl -u photobooth -b
```

> Rule of thumb: booth is completely dead → check journalctl first. Booth is running but behaving wrong → check the app log.

---

## Starting, Stopping, Restarting Flask

**Restart** — after changing `.env` or deploying new code:
```bash
systemctl restart photobooth
```

**Stop** — to take the booth offline for testing a new feature:
```bash
systemctl stop photobooth
```
The booth is now unreachable. Test whatever you need, then bring it back:

**Start** — to bring the booth back online:
```bash
systemctl start photobooth
```

Check it came back up:
```bash
systemctl status photobooth
```

You should see `Active: active (running)` within a few seconds.

> Stop it during a quiet period — nobody can use the booth while it's stopped. Most changes take under a minute.

---

## Changing a Setting

All tunable values live in `.env`. Edit it directly on the Pi:
```bash
nano .env
```

Make your change, save (`Ctrl+X → Y → Enter`), then restart:
```bash
systemctl restart photobooth
```

Common things to adjust remotely:
- `INACTIVITY_TIMEOUT_SECS` — if the booth is resetting too quickly or too slowly
- `PROCESSING_RESET_SECS` — if customers need more time to scan the QR
- `COUNTDOWN_SECS` — if groups need more time to get ready
- `STRIP_JPEG_QUALITY` — if print quality needs tuning
- `BOOTH_BASE_URL` — if the Cloudflare tunnel URL changes

---

## Deploying a Code Update

```bash
cd ~/Photo_Booth
git pull
systemctl restart photobooth
```

Three commands. The booth applies the update within seconds.

---

## Checking Disk Space

Sessions accumulate. Check how much is left:
```bash
df -h
```

See how much the sessions folder is using:
```bash
du -sh app/sessions/
```

Count how many sessions are stored:
```bash
ls app/sessions/ | wc -l
```

Manually delete sessions older than 24 hours (run this carefully):
```bash
find app/sessions/ -maxdepth 1 -type d -mtime +1 -exec rm -rf {} +
```

> Once session cleanup is automated (see WHATS_NEXT.md), you won't need to do this manually.

---

## Checking the Camera

If the preview is black or frozen, check whether the camera is visible to the OS:
```bash
ls /dev/video*
```

You should see `/dev/video0` (or whatever `CAMERA_INDEX` is set to). If nothing shows, the camera is physically disconnected or the driver isn't loaded.

Restart Flask after reconnecting:
```bash
systemctl restart photobooth
```

---

## Checking the NFC Reader

If cards aren't being detected, confirm the reader is connected:
```bash
lsusb | grep 1A86
```

You should see a line with `1a86:dd01`. If nothing shows, it's not connected.

Also check the reader log:
```bash
grep -i nfc logs/photobooth.log
grep -i reader logs/photobooth.log
```

---

## What You Can't Fix Remotely

Some things require physical access:

| Problem | Why remote won't work |
|---|---|
| Pi won't boot | SSH tunnel isn't up — can't get in |
| SD card corrupted | Needs reflashing |
| Camera physically dead | Hardware swap |
| NFC reader unplugged | Needs to be plugged back in |
| No power | Nothing to SSH into |

For these, someone needs to go to the booth. That's the main reason to know someone physically nearby the first few weeks.

---

## Quick Reference

```bash
# Check both services
systemctl status photobooth cloudflared

# Restart Flask
systemctl restart photobooth

# Live app log
tail -f ~/Photo_Booth/logs/photobooth.log

# Live system log
journalctl -u photobooth -f

# Edit config
nano ~/Photo_Booth/.env && systemctl restart photobooth

# Deploy update
cd ~/Photo_Booth && git pull && systemctl restart photobooth

# Disk check
df -h && du -sh ~/Photo_Booth/app/sessions/
```
