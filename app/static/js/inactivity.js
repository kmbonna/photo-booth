// Inactivity timeout — resets the booth to the welcome screen when nobody
// has interacted for INACTIVITY_TIMEOUT_MS milliseconds.
//
// window.INACTIVITY_TIMEOUT_MS is injected by Flask (from the .env file)
// into index.html so it can be changed without touching this file.
//
// Public API (used by app.js):
//   inactivity.pause()  — call when the camera countdown starts
//   inactivity.resume() — call when leaving the camera screen
//   inactivity.reset()  — call to restart the countdown manually

const inactivity = (() => {
    const ms = window.INACTIVITY_TIMEOUT_MS || 300_000; // default 5 min

    let timer  = null;
    let paused = false;

    function _fire() {
        logEvent('inactivity timeout'); // defined in app.js
        resetBooth();
    }

    function reset() {
        if (paused) return;
        clearTimeout(timer);
        timer = setTimeout(_fire, ms);
    }

    function pause() {
        paused = true;
        clearTimeout(timer);
    }

    function resume() {
        paused = false;
        reset();
    }

    // Restart the countdown on any user interaction.
    ['click', 'touchstart', 'mousemove', 'keydown'].forEach(evt => {
        document.addEventListener(evt, reset, { passive: true });
    });

    // Start the timer immediately on page load.
    reset();

    return { reset, pause, resume };
})();
