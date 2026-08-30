import logging
import os
import uuid

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from modules import log, reader
from modules.camera import capture_photo, generate_preview
from modules.composer import compose
from modules.qr import generate_qr_bytes

logger = log.get('main')

# Suppress werkzeug request-line logs (GET /... 200) — app logs tell the full story.
logging.getLogger('werkzeug').setLevel(logging.WARNING)

logger.info("booth starting up")

app = Flask(__name__)


def _ctx(visitor=None, session=None):
    """Build the extra dict for log calls."""
    return {
        'visitor': visitor or request.args.get('visitor_id', '-'),
        'session': session or '-',
    }


@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, HTTPException):
        return e
    logger.exception("unhandled error: %s", e)
    return jsonify({'status': 'error', 'message': str(e)}), 500


# ── GET /
@app.route('/')
def index():
    return render_template('index.html',
        inactivity_timeout_ms = int(os.environ.get('INACTIVITY_TIMEOUT_SECS', 300)) * 1000,
        processing_reset_ms   = int(os.environ.get('PROCESSING_RESET_SECS', 60)) * 1000,
        photos_per_session    = int(os.environ.get('PHOTOS_PER_SESSION', 4)),
        countdown_secs        = int(os.environ.get('COUNTDOWN_SECS', 3)),
    )


# ── POST /event
# JS calls this for navigation steps that have no other server call.
# → app.js  logEvent()
@app.route('/event', methods=['POST'])
def log_ui_event():
    data    = request.get_json(silent=True) or {}
    event   = data.get('event', '?')
    visitor = data.get('visitor_id', '-')
    session = data.get('session_id', '-')
    logger.info(event, extra={'visitor': visitor, 'session': session})
    return jsonify({'ok': True})


# ── GET /preview
# Streams live MJPEG frames. Kept open for the duration of the camera screen.
# → modules/camera.py  generate_preview()
@app.route('/preview')
def preview():
    return Response(generate_preview(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ── GET /payment/wait
# Blocks until a card is tapped or PAYMENT_TIMEOUT_SECS elapses.
# → modules/reader.py  wait_for_tap()  →  app.js  startPaymentFlow()
@app.route('/payment/wait')
def payment_wait():
    uid = reader.wait_for_tap(timeout=int(os.environ.get('PAYMENT_TIMEOUT_SECS', 60)))
    if uid:
        logger.info("card tapped · uid=%s", uid, extra=_ctx())
        return jsonify({'status': 'ok', 'uid': uid})
    logger.info("payment timed out — no card", extra=_ctx())
    return jsonify({'status': 'timeout'}), 408


# ── GET /new_session
# Generates a session ID and returns it. No files created yet.
# → app.js  startCameraSession()
@app.route('/new_session')
def new_session():
    session_id = str(uuid.uuid4())[:8]
    logger.info("session started", extra=_ctx(session=session_id))
    return jsonify({'session_id': session_id})


# ── GET /capture/<session_id>/<photo_num>
# Grabs the latest camera frame and saves it as photo_N.jpg.
# → modules/camera.py  capture_photo()  →  app.js  triggerCapture()
@app.route('/capture/<session_id>/<int:photo_num>')
def capture(session_id, photo_num):
    total = int(os.environ.get('PHOTOS_PER_SESSION', 4))
    path  = capture_photo(session_id, photo_num)
    ctx   = _ctx(session=session_id)
    if path:
        logger.info("photo %d/%d", photo_num, total, extra=ctx)
        return jsonify({'status': 'ok', 'photo': photo_num})
    logger.error("photo %d/%d FAILED", photo_num, total, extra=ctx)
    return jsonify({'status': 'error'}), 500


# ── GET /compose/<session_id>
# Crops, resizes, and stitches all photos into strip.jpg.
# → modules/composer.py  compose()  →  app.js  showStrip()
@app.route('/compose/<session_id>')
def compose_strip(session_id):
    ctx = _ctx(session=session_id)
    logger.info("composing strip", extra=ctx)
    try:
        compose(session_id)
        logger.info("strip done", extra=ctx)
        return jsonify({'status': 'ok'})
    except FileNotFoundError as e:
        logger.error("strip failed — %s", e, extra=ctx)
        return jsonify({'status': 'error', 'message': str(e)}), 404


# ── GET /qr/<session_id>
# Generates and serves a QR code encoding the strip's public URL.
# → modules/qr.py  generate_qr_bytes()  →  app.js  showStrip()
@app.route('/qr/<session_id>')
def serve_qr(session_id):
    buf = generate_qr_bytes(session_id)
    return send_file(buf, mimetype='image/png')


# ── GET /strip/<session_id>
# Serves strip.jpg directly. Used by the processing screen and the QR code URL.
@app.route('/strip/<session_id>')
def serve_strip(session_id):
    sessions_dir = os.environ.get('SESSIONS_DIR') or os.path.join(os.path.dirname(__file__), 'sessions')
    path = os.path.join(sessions_dir, session_id, 'strip.jpg')
    if not os.path.exists(path):
        return jsonify({'status': 'not_found'}), 404
    return send_file(path, mimetype='image/jpeg')


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)
