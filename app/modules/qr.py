import io
import os
import qrcode
import qrcode.constants

from modules import log
logger = log.get(__name__)

def strip_url(session_id):
    base = os.environ.get('BOOTH_BASE_URL', 'http://localhost:5000')
    return f"{base}/strip/{session_id}"


def generate_qr_bytes(session_id):
    """Return a PNG BytesIO of the QR code for this session's strip URL."""
    url = strip_url(session_id)
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error("QR generation failed for session %s: %s", session_id, e)
        raise
