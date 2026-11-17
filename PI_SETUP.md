# Pi Connection Guide

## SSH In (from anywhere)

Double-click **ssh-pi.bat** on the Desktop, or run:

```
ssh pbpi-1@100.69.73.14
```

Requires Tailscale to be running on your laptop (system tray, bottom right).
Password: whatever you set in Raspberry Pi Imager.

---

## SSH In (local network only — no Tailscale)

Both your laptop and Pi must be on the same WiFi.

```
ssh pbpi-1@<pi-ip>
```

To find the Pi's IP:

```
arp -a | findstr "dc-a6-32"
```

The IP in that line is the Pi.

---

## Add a New WiFi Network

See what's already saved:
```bash
nmcli con show
```

See the password of a saved network:
```bash
sudo nmcli con show "NetworkName" | grep psk
```

Add a new network:
```bash
sudo nmcli con add type wifi ifname wlan0 con-name "NetworkName" ssid "NetworkName" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "password"
```

Replace `NetworkName` and `password`. The Pi connects automatically whenever it's in range.

---

## Rescue Network (do this on every Pi)

If the Pi loses its normal WiFi (venue changed the password, login page expired, router died), there is no way to reach it remotely. To avoid getting locked out, every Pi has a **rescue network** saved, with the highest priority:

```bash
sudo nmcli con add type wifi ifname wlan0 con-name booth-rescue ssid booth-rescue wifi-sec.key-mgmt wpa-psk wifi-sec.psk "RESCUE_PASSWORD"
sudo nmcli con modify booth-rescue connection.autoconnect-priority 100
```

Pick one password for `RESCUE_PASSWORD`, use it on every booth, and keep it somewhere safe. It is not stored in this repo.

Check it's saved:
```bash
nmcli con show | grep booth-rescue
```

**When a booth goes offline:**
1. You (or anyone at the venue) turn on a phone or laptop hotspot named exactly `booth-rescue` with the rescue password. This is case-sensitive, and the hotspot must have internet.
2. Within 1–2 minutes the Pi joins it. If not, unplug and replug the Pi.
3. SSH in through Tailscale as usual (`ssh pbpi-1@100.69.73.14`).
4. Fix or add the real network (see "Add a New WiFi Network" above), then turn the hotspot off.

> Also avoid venue WiFi with a login/"Accept" page. The Pi can't log in, and those logins expire.

---

## Connect to a Saved Network Manually

```bash
sudo nmcli con up "NetworkName"
```

---

## Check Pi's Current IP

```bash
hostname -I
```

---

## Restart the Pi

```bash
sudo reboot
```

---

## Basic Navigation Commands

```bash
pwd                  # show current folder
ls                   # list files in current folder
ls -la               # list with details + hidden files
cd folder-name       # go into a folder
cd ..                # go up one folder
cd ~                 # go back to home directory
cat filename         # print file contents
nano filename        # edit a file (Ctrl+X to exit, Y to save)
mkdir folder-name    # create a folder
rm filename          # delete a file
rm -rf folder-name   # delete a folder and everything in it
cp file1 file2       # copy a file
mv file1 file2       # rename or move a file
```

---

## Managing the Photobooth Service

The app runs as a systemd service called `photobooth`. It starts automatically on boot and restarts itself if it crashes.

**Check if it's running:**
```bash
sudo systemctl status photobooth
```

**Stop it** (e.g. before pulling a code update):
```bash
sudo systemctl stop photobooth
```

**Start it again:**
```bash
sudo systemctl start photobooth
```

**Restart it** (after a code change or `.env` edit):
```bash
sudo systemctl restart photobooth
```

**Disable auto-start** (if you want it to stay off after a reboot):
```bash
sudo systemctl disable photobooth
```

**Re-enable auto-start:**
```bash
sudo systemctl enable photobooth
```

**Deploy a code update cleanly:**
```bash
sudo systemctl stop photobooth
cd ~/photo-booth && git pull
sudo systemctl start photobooth
```

**View live logs:**
```bash
journalctl -u photobooth -f
```

---

## Pi Details

| | |
|---|---|
| Hostname | photobooth-1 |
| Username | pbpi-1 |
| Tailscale IP | 100.69.73.14 |
| MAC address | dc:a6:32:2c:65:c2 |
