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
