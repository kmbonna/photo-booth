import os
import queue
import string
import sys
import threading
import time

from modules import log
logger = log.get(__name__)

_DEV_MODE = sys.platform == "win32"
_card_queue = queue.Queue()
_running = False
_thread = None


def _dev_loop():
    # Simulate a card tap every 3 seconds so any wait_for_tap() call resolves quickly.
    global _running
    while _running:
        time.sleep(3)
        if _running:
            _card_queue.put("DEV-CARD-XXXXXXXX")


def _reader_loop():
    # On Linux/Pi: find the NFC reader by VID/PID and read key events from it directly.
    # The reader presents as a HID keyboard and sends the card UID as keystrokes + Enter.
    try:
        import evdev
        from evdev import categorize, ecodes
    except ImportError:
        logger.error("evdev not installed — NFC reader will not work. Run: pip install evdev")
        return

    device = None
    vendor_id  = int(os.environ.get('NFC_VENDOR_ID',  '0x1A86'), 16)
    product_id = int(os.environ.get('NFC_PRODUCT_ID', '0xDD01'), 16)

    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
            if d.info.vendor == vendor_id and d.info.product == product_id:
                device = d
                break
        except Exception:
            continue

    if device is None:
        logger.error("NFC reader (VID_1A86 PID_DD01) not found — check USB connection")
        return

    logger.info("NFC reader found: %s", device.path)

    alpha_map = {
        getattr(ecodes, f'KEY_{c.upper()}'): c
        for c in string.ascii_lowercase
        if hasattr(ecodes, f'KEY_{c.upper()}')
    }
    digit_map = {
        ecodes.KEY_0: '0', ecodes.KEY_1: '1', ecodes.KEY_2: '2',
        ecodes.KEY_3: '3', ecodes.KEY_4: '4', ecodes.KEY_5: '5',
        ecodes.KEY_6: '6', ecodes.KEY_7: '7', ecodes.KEY_8: '8',
        ecodes.KEY_9: '9',
    }
    key_map = {**alpha_map, **digit_map}

    buf = []
    try:
        for event in device.read_loop():
            if not _running:
                break
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == evdev.KeyEvent.key_down:
                    if key_event.scancode == ecodes.KEY_ENTER:
                        if buf:
                            uid = ''.join(buf)
                            logger.info("Card tapped: uid=%s", uid)
                            _card_queue.put(uid)
                            buf.clear()
                    elif key_event.scancode in key_map:
                        buf.append(key_map[key_event.scancode])
    except Exception as e:
        logger.error("NFC reader disconnected or read error: %s", e)


def start():
    global _running, _thread
    if _running:
        return
    _running = True
    loop = _dev_loop if _DEV_MODE else _reader_loop
    _thread = threading.Thread(target=loop, daemon=True)
    _thread.start()


def wait_for_tap(timeout=60):
    """Block until a card is tapped. Returns uid string or None on timeout."""
    start()
    # Drain any stale taps from previous sessions so each call gets a fresh read.
    while not _card_queue.empty():
        try:
            _card_queue.get_nowait()
        except queue.Empty:
            break
    try:
        return _card_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def stop():
    global _running
    _running = False