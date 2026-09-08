// ── Camera readiness polling ─────────────────────────────
function _setCameraReady(ready) {
    document.getElementById('welcome-start-btn').style.display = ready ? '' : 'none';
    document.getElementById('welcome-oos').style.display       = ready ? 'none' : 'block';
}

function _checkCamera() {
    fetch('/camera/ready')
        .then(r => r.json())
        .then(d => _setCameraReady(d.ready))
        .catch(() => _setCameraReady(false));
}

_checkCamera();
setInterval(_checkCamera, 5000);

// ── Processing screen countdown ──────────────────────────
let _processingTimer = null;

function startProcessingCountdown() {
    const block     = document.getElementById('reset-countdown');
    const secondsEl = document.getElementById('reset-seconds');
    let remaining   = Math.round((window.PROCESSING_RESET_MS || 60000) / 1000);

    block.style.display = 'block';
    secondsEl.textContent = remaining;

    clearInterval(_processingTimer);
    _processingTimer = setInterval(() => {
        remaining--;
        secondsEl.textContent = remaining;
        if (remaining <= 0) {
            clearInterval(_processingTimer);
            resetBooth();
        }
    }, 1000);
}

function extendProcessingTimer() {
    clearInterval(_processingTimer);
    startProcessingCountdown();
}

// ── Server-side event logging ────────────────────────────
let visitorId = null; // short ID assigned when someone starts the flow, for funnel tracking

function logEvent(event) {
    fetch('/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, visitor_id: visitorId || '-', session_id: sessionId || '-' })
    }).catch(() => {});
}

// ── Screen transitions ───────────────────────────────────
function goTo(targetId) {
    const current = document.querySelector('.screen.active');
    const target = document.getElementById(targetId);
    if (!target || current === target) return;

    current.classList.add('exit');
    setTimeout(() => {
        current.classList.remove('active', 'exit');
        target.classList.add('active');
    }, 400);
}

// ── Payment flow ─────────────────────────────────────────
let paymentController = null;
let selectedCopies = 1;
let selectedMood = 'default';

function _formatPrice(p) {
    return p % 1 === 0 ? `${p} ${window.CURRENCY}` : `${p.toFixed(2)} ${window.CURRENCY}`;
}

// Inactivity timer is only active on steps and payment — the two screens
// where a customer can abandon the flow and walk away mid-session.
function goToSteps() {
    visitorId = Math.random().toString(36).slice(2, 7); // e.g. "x7a2f"
    logEvent('Customer pressed: welcome screen → steps screen');
    inactivity.resume();
    goTo('screen-steps');
}

document.getElementById('steps-price').textContent = _formatPrice(window.PRICES[0]);

function goToCopies() {
    logEvent('steps → copies');
    inactivity.resume();

    const grid = document.getElementById('copies-grid');
    grid.innerHTML = '';
    for (let i = 1; i <= window.PRICES.length; i++) {
        const price = window.PRICES[i - 1];
        const btn = document.createElement('button');
        btn.className = 'btn-copies';
        btn.innerHTML = `<span class="copies-num">${i}</span><span class="copies-price">${_formatPrice(price)}</span>`;
        btn.onclick = () => selectCopies(i);
        grid.appendChild(btn);
    }

    goTo('screen-copies');
}

function selectCopies(n) {
    selectedCopies = n;
    goToMood();
}

function goToMood() {
    logEvent('copies → mood');
    inactivity.resume();
    goTo('screen-mood');
}

function selectMood(mood) {
    selectedMood = mood;
    goToPayment();
}

function goToPayment() {
    logEvent('mood → payment');
    inactivity.resume();

    const price = window.PRICES[selectedCopies - 1];
    document.getElementById('payment-price').textContent = _formatPrice(price);
    document.getElementById('payment-copies-label').textContent =
        selectedCopies === 1 ? '1 copy · print + digital included' : `${selectedCopies} copies · print + digital included`;

    goTo('screen-payment');
    if (window.PAYMENT_DEV_MODE) {
        document.getElementById('dev-pay-btn').style.display = 'block';
    } else {
        setTimeout(startPaymentFlow, 700);
    }
}

async function startPaymentFlow() {
    if (paymentController) paymentController.abort();
    paymentController = new AbortController();

    const zone   = document.getElementById('tap-zone');
    const status = document.getElementById('tap-status');

    zone.className   = 'tap-zone';
    status.textContent = '';
    status.className   = 'tap-status';

    try {
        const res  = await fetch(`/payment/wait?visitor_id=${visitorId || '-'}`, { signal: paymentController.signal });
        const data = await res.json();

        if (data.status === 'ok') {
            zone.className     = 'tap-zone approved';
            status.textContent = 'Approved!';
            status.className   = 'tap-status approved';
            setTimeout(startCameraSession, 1200);
        } else {
            status.textContent = 'Timed out — tap again';
            status.className   = 'tap-status error';
            setTimeout(startPaymentFlow, 2000);
        }
    } catch (e) {
        if (e.name !== 'AbortError') {
            status.textContent = 'Connection error — retrying…';
            status.className   = 'tap-status error';
            setTimeout(startPaymentFlow, 3000);
        }
    }
}

function cancelPayment() {
    if (paymentController) {
        paymentController.abort();
        paymentController = null;
    }
    inactivity.resume();
    goTo('screen-mood');
}

// ── Error handling ───────────────────────────────────────
// paymentConfirmed tracks whether money has been taken this session.
// Post-payment errors show session ID + "contact staff" instead of "try again".
let paymentConfirmed = false;

function showError(title, message) {
    document.getElementById('error-title').innerHTML = `<em>${title}</em>`;
    document.getElementById('error-message').textContent = message;

    const sessionBlock = document.getElementById('error-session');
    const primaryBtn   = document.getElementById('error-btn-primary');
    const secondaryBtn = document.getElementById('error-btn-secondary');

    if (paymentConfirmed && sessionId) {
        // Post-payment: show session ID so staff can recover photos from disk.
        document.getElementById('error-session-id').textContent = sessionId.toUpperCase();
        sessionBlock.style.display = 'flex';
        primaryBtn.textContent  = 'Run Diagnostics';
        primaryBtn.onclick      = null; // no action — user must speak to staff
        secondaryBtn.style.display = 'block';
        secondaryBtn.textContent   = 'Start Over';
        secondaryBtn.onclick       = resetBooth;
    } else {
        // Pre-payment: simple retry.
        sessionBlock.style.display  = 'none';
        primaryBtn.textContent  = 'Try Again';
        primaryBtn.onclick      = resetBooth;
        secondaryBtn.style.display  = 'none';
    }

    inactivity.pause(); // error screen has no timeout — customer must press a button
    goTo('screen-error');
}

// ── Camera session state ─────────────────────────────────
let sessionId = null;
let photosTaken = 0;
let capturing = false;  // guard against double-firing countdown
let stripShown = false; // guard against double compose
let _poseQueue = [];
let _poseIndex = 0;
const TOTAL_PHOTOS   = window.PHOTOS_PER_SESSION || 4;
const COUNTDOWN_FROM = window.COUNTDOWN_SECS     || 3;

async function _waitForCamera(maxWaitMs) {
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
        try {
            const res = await fetch('/camera/ready');
            const d   = await res.json();
            if (d.ready) return true;
        } catch (_) {}
        await new Promise(r => setTimeout(r, 1000));
    }
    return false;
}

async function startCameraSession() {
    paymentConfirmed = true; // payment just cleared — errors from here are post-payment
    inactivity.pause(); // camera countdown is automated — no user interaction expected

    const ready = await _waitForCamera(10000);
    if (!ready) {
        showError('Camera not ready', 'The camera is not responding. Please note your session ID below and try again shortly.');
        return;
    }

    try {
        const res  = await fetch(`/new_session?visitor_id=${visitorId || '-'}`);
        const data = await res.json();
        sessionId   = data.session_id;
        photosTaken = 0;
        _poseQueue  = [...POSES].sort(() => Math.random() - 0.5);
        _poseIndex  = 0;
        goTo('screen-camera');
        setTimeout(runCountdown, 700);
    } catch (e) {
        showError('Connection error', 'Could not start your session. Please try again.');
    }
}

// ── Countdown + capture loop ─────────────────────────────
let _countdownInterval = null;

function runCountdown() {
    clearInterval(_countdownInterval); // kill any phantom interval from a previous round
    updateCounter();
    let count = COUNTDOWN_FROM;

    const el              = document.getElementById('countdown');
    const captureFeedback = document.getElementById('capture-feedback');
    const pose            = document.getElementById('pose-suggestion');

    captureFeedback.textContent = '';
    captureFeedback.classList.remove('show');
    pose.textContent = _poseQueue[_poseIndex++] || '';

    showNumber(el, count);

    _countdownInterval = setInterval(() => {
        el.classList.add('shrink');

        setTimeout(() => {
            count--;
            if (count > 0) {
                showNumber(el, count);
                clearTransition(el);
            } else {
                el.classList.remove('show', 'shrink');
                clearInterval(_countdownInterval);
                _countdownInterval = null;
                triggerCapture(captureFeedback);
            }
        }, 220);

    }, 1000);
}

function showNumber(el, num) {
    el.textContent = num;
    el.classList.remove('shrink');
    void el.offsetWidth; // force reflow so transition fires
    el.classList.add('show');
}

function clearTransition(el) {
    el.classList.remove('shrink');
    void el.offsetWidth;
    el.classList.add('show');
}

// ── Take the photo ───────────────────────────────────────
async function triggerCapture(captureFeedbackEl) {
    if (capturing) return;
    capturing = true;
    triggerFlash();
    captureFeedbackEl.textContent = 'Got it!';
    captureFeedbackEl.classList.add('show');

    // Retry up to 3 times — camera may momentarily drop a frame
    let success = false;
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const res  = await fetch(`/capture/${sessionId}/${photosTaken + 1}?visitor_id=${visitorId || '-'}`);
            const data = await res.json();
            if (data.status === 'ok') { success = true; break; }
        } catch (_) {}
        await new Promise(r => setTimeout(r, 800));
    }

    if (!success) {
        capturing = false;
        showError('Camera issue', 'We couldn\'t save your photo. Please contact staff — your session is recorded below.');
        return;
    }

    photosTaken++;
    capturing = false;

    if (photosTaken < TOTAL_PHOTOS) {
        setTimeout(() => {
            captureFeedbackEl.classList.remove('show');
            setTimeout(runCountdown, 400);
        }, 1200);
    } else {
        setTimeout(() => showStrip(), 1400);
    }
}

// ── Strip + processing screen ────────────────────────────
async function showStrip() {
    if (stripShown) return;
    stripShown = true;
    // Timer stays paused here — customer is waiting on the machine, not idle.
    // It resumes only once the strip is visible and they can actually scan the QR.
    goTo('screen-processing');

    const img    = document.getElementById('strip-img');
    const status = document.getElementById('strip-status');

    img.classList.remove('loaded');
    status.textContent = 'Developing your film…';

    // Ask server to compose the strip
    try {
        const res = await fetch(`/compose/${sessionId}?mood=${selectedMood}&visitor_id=${visitorId || '-'}`);
        if (!res.ok) throw new Error('Compose failed');

        img.onload = () => {
            img.classList.add('loaded');
            startProcessingCountdown();
        };
        img.src = `/strip/${sessionId}?t=${Date.now()}`;
        status.textContent = 'Ready to share!';

        // Show QR code
        const qrBlock = document.getElementById('qr-block');
        const qrImg   = document.getElementById('qr-img');
        qrImg.src = `/qr/${sessionId}`;
        qrBlock.style.display = 'flex';
    } catch (e) {
        showError('Processing error', 'We couldn\'t compose your strip. your photos are saved.');
    }
}

function resetBooth() {
    if (paymentController) {
        paymentController.abort();
        paymentController = null;
    }
    clearInterval(_processingTimer);
    clearInterval(_countdownInterval);
    _countdownInterval = null;
    document.getElementById('reset-countdown').style.display = 'none';
    document.getElementById('dev-pay-btn').style.display = 'none';
    if (sessionId) logEvent(`session reset`);
    inactivity.pause();
    sessionId        = null;
    visitorId        = null;
    photosTaken      = 0;
    selectedCopies   = 1;
    selectedMood     = 'default';
    paymentConfirmed = false;
    capturing        = false;
    stripShown       = false;
    _poseQueue       = [];
    _poseIndex       = 0;
    const img = document.getElementById('strip-img');
    img.src = '';
    img.classList.remove('loaded');
    document.getElementById('qr-block').style.display = 'none';
    document.getElementById('qr-img').src = '';
    goTo('screen-welcome');
}

// ── Flash ────────────────────────────────────────────────
function triggerFlash() {
    const flash = document.getElementById('flash');
    flash.classList.add('active');
    setTimeout(() => flash.classList.remove('active'), 120);
}

// ── Counter label ────────────────────────────────────────
function updateCounter() {
    const el = document.getElementById('photo-counter');
    el.textContent = `Photo ${photosTaken + 1} of ${TOTAL_PHOTOS}`;
}
