import glob
import subprocess
import cv2
import numpy as np
import os
import threading
import time

from modules import log
logger = log.get(__name__)

_latest_frame = None
_running = False
_lock = threading.Lock()
_thread = None


def _resolve_camera_index():
    """Find camera by USB vendor/product ID, fall back to CAMERA_INDEX env var."""
    vendor  = os.environ.get('CAMERA_VENDOR_ID', '').lower()
    product = os.environ.get('CAMERA_PRODUCT_ID', '').lower()

    if vendor and product:
        for dev in sorted(glob.glob('/dev/video*')):
            try:
                out = subprocess.check_output(
                    ['udevadm', 'info', f'--name={dev}'], text=True, stderr=subprocess.DEVNULL)
                if vendor in out and product in out:
                    idx = int(''.join(filter(str.isdigit, dev.replace('/dev/video', ''))))
                    logger.info("Camera found at %s (vendor=%s product=%s)", dev, vendor, product)
                    return idx
            except Exception:
                continue
        logger.warning("Camera not found by USB ID — falling back to CAMERA_INDEX")

    return int(os.environ.get('CAMERA_INDEX', 0))


def _placeholder_loop():
    global _latest_frame
    logger.warning("Windows detected — camera disabled, serving placeholder frames")
    placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
    placeholder[:] = (30, 30, 30)
    cv2.putText(placeholder, 'NO CAMERA', (480, 360),
                cv2.FONT_HERSHEY_SIMPLEX, 3, (80, 80, 80), 4)
    while _running:
        with _lock:
            _latest_frame = placeholder
        time.sleep(0.1)


def _camera_loop():
    global _latest_frame, _running

    if os.name == 'nt':
        _placeholder_loop()
        return

    while _running:
        idx = _resolve_camera_index()
        cam = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not cam.isOpened():
            logger.warning("Camera failed to open at index %d — retrying in 5s", idx)
            cam.release()
            time.sleep(5)
            continue

        logger.info("Camera opened at index %d", idx)
        for _ in range(30):  # flush stale frames on startup
            cam.read()

        consecutive_failures = 0
        while _running:
            ret, frame = cam.read()
            if ret:
                consecutive_failures = 0
                with _lock:
                    _latest_frame = cv2.flip(frame, 1)
            else:
                consecutive_failures += 1
                if consecutive_failures == 10:
                    logger.warning("Camera: 10 consecutive read failures")
                elif consecutive_failures >= 50:
                    logger.error("Camera: 50 consecutive failures — releasing and re-scanning")
                    break
                time.sleep(0.05)

        cam.release()
        if _running:
            logger.info("Camera released — attempting recovery in 3s")
            time.sleep(3)

    logger.info("Camera thread stopped")


def start():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_camera_loop, daemon=True)
    _thread.start()
    time.sleep(3)  # let camera warm up


def generate_preview():
    start()
    interval = 1.0 / int(os.environ.get('PREVIEW_FPS', 15))
    while True:
        t = time.time()
        with _lock:
            frame = _latest_frame.copy() if _latest_frame is not None else None
        if frame is None:
            time.sleep(0.03)
            continue
        quality = int(os.environ.get('PREVIEW_JPEG_QUALITY', 75))
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
        elapsed = time.time() - t
        if elapsed < interval:
            time.sleep(interval - elapsed)


def capture_photo(session_id, photo_number):
    with _lock:
        frame = _latest_frame.copy() if _latest_frame is not None else None
    if frame is None:
        logger.error("capture_photo: no frame available (session=%s photo=%d)", session_id, photo_number)
        return None
    base = os.environ.get('SESSIONS_DIR') or os.path.join(os.path.dirname(__file__), '..', 'sessions')
    session_dir = os.path.join(base, session_id)
    os.makedirs(session_dir, exist_ok=True)
    path = os.path.join(session_dir, f'photo_{photo_number}.jpg')
    if not cv2.imwrite(path, frame):
        logger.error("capture_photo: imwrite failed (path=%s)", path)
        return None
    return path


def is_ready():
    with _lock:
        return _latest_frame is not None


def stop():
    global _running
    _running = False
    if _thread:
        _thread.join(timeout=2)
