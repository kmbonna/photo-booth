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

## see the connections already there:

nmcli con show

## see the password of a network

sudo nmcli con show "NetworkName" | grep psk

SSH into the Pi, then run:

```bash
sudo nmcli con add type wifi ifname wlan0 con-name "NetworkName" ssid "NetworkName" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "password"
```

Replace `NetworkName` and `password`. The Pi will connect automatically whenever it's in range.

---

## See All Saved WiFi Networks

```bash
nmcli con show
```

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

## Pi Details

| | |
|---|---|
| Hostname | photobooth-1 |
| Username | pbpi-1 |
| Tailscale IP | 100.69.73.14 |
| MAC address | dc:a6:32:2c:65:c2 |
