// monitoring.js
// Optional auto-run: asks the server for one new SIMULATED measurement
// every 5 seconds, then reloads the page. Stops when the run is complete.

(function () {
    var form = document.getElementById("monitor-form");
    var autoBtn = document.getElementById("auto-btn");
    if (!form || !autoBtn) return;

    var KEY = "neurotriage_autorun";
    var timer = null;

    function isOn() {
        return sessionStorage.getItem(KEY) === "1";
    }

    function setLabel() {
        autoBtn.textContent = isOn() ? "Stop auto-run" : "Start auto-run (every 5 s)";
    }

    function stop() {
        sessionStorage.removeItem(KEY);
        if (timer) clearTimeout(timer);
        setLabel();
    }

    function runOnce() {
        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "fetch" }
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.ok || data.finished) sessionStorage.removeItem(KEY);
                window.location.reload();
            })
            .catch(function () { stop(); });
    }

    autoBtn.addEventListener("click", function () {
        if (isOn()) {
            stop();
        } else {
            sessionStorage.setItem(KEY, "1");
            setLabel();
            runOnce();
        }
    });

    setLabel();
    if (isOn()) {
        timer = setTimeout(runOnce, 5000);
    }
})();