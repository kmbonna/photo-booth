import cv2
import os
import sys
import threading
import time
import numpy as np

from modules import log
logger = log.get(__name__)

_latest_frame = None
_running = False
_lock = threading.Lock()
_thread = None

# On Windows, real camera access through OpenCV is blocked by the Windows
# Camera Frame Server (post-2019 architecture). Use a dev-mode placeholder
# so the full UI can be tested. On Linux (Raspberry Pi), the real camera works.
_DEV_MODE = sys.platform == "win32"


def _make_dev_frame():
    """Generate a fake camera frame for Windows dev mode."""
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:] = (40, 35, 30)  # dark warm background
    cv2.putText(frame, "CAMERA DEV MODE", (360, 340),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, (120, 160, 200), 3, cv2.LINE_AA)
    cv2.putText(frame, "Windows only - real camera active on Pi", (310, 410),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (90, 120, 150), 2, cv2.LINE_AA)
    return frame


def _dev_loop():
    global _latest_frame, _running
    while _running:
        frame = _make_dev_frame()
        # Animate a simple pulsing dot so the preview looks live
        t = time.time()
        cx, cy = 640, 550
        r = int(10 + 6 * abs(np.sin(t * 2)))
        color = (0, int(180 + 60 * abs(np.sin(t * 2))), 0)
        cv2.circle(frame, (cx, cy), r, color, -1)
        with _lock:
            _latest_frame = frame
        time.sleep(0.033)  # ~30 fps


def _camera_loop():
    global _latest_frame, _running
    cam = cv2.VideoCapture(int(os.environ.get('CAMERA_INDEX', 0)))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    if not cam.isOpened():
        logger.error("Camera failed to open — check connection and index")
        _running = False
        return

    logger.info("Camera opened successfully")

    for _ in range(30):
        cam.read()

    consecutive_failures = 0
    while _running:
        ret, frame = cam.read()
        if ret:
            consecutive_failures = 0
            frame = cv2.flip(frame, 1)
            with _lock:
                _latest_frame = frame
        else:
            consecutive_failures += 1
            if consecutive_failures == 10:
                logger.warning("Camera: 10 consecutive read failures")
            elif consecutive_failures == 50:
                logger.error("Camera: 50 consecutive read failures — camera may be disconnected")
            time.sleep(0.05)

    cam.release()
    logger.info("Camera released")


def start():
    global _running, _thread
    if _running:
        return
    _running = True
    loop = _dev_loop if _DEV_MODE else _camera_loop
    _thread = threading.Thread(target=loop, daemon=True)
    _thread.start()
    if not _DEV_MODE:
        time.sleep(3)  # let real camera warm up


def generate_preview():
    start()
    while True:
        with _lock:
            frame = _latest_frame.copy() if _latest_frame is not None else None
        if frame is None:
            time.sleep(0.03)
            continue
        quality = int(os.environ.get('PREVIEW_JPEG_QUALITY', 75))
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
               + buffer.tobytes() + b'\r\n')


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
    ok = cv2.imwrite(path, frame)
    if not ok:
        logger.error("capture_photo: imwrite failed — disk full? (path=%s)", path)
        return None
    return path


def stop():
    global _running
    _running = False
    if _thread:
        _thread.join(timeout=2)
