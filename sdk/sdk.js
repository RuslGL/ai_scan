<script>
(function () {
    const EP = "https://api.ai-scan.tech/track";

    const ua = navigator.userAgent;
    const isSamsung = /SamsungBrowser/i.test(ua);

    function gen() {
        return Math.random().toString(36).slice(2) + Date.now();
    }

    function safeStorage(storage, key) {
        try {
            return storage[key] || (storage[key] = gen());
        } catch {
            return gen();
        }
    }

    const uid = safeStorage(localStorage, "ais_uid");
    const sid = safeStorage(sessionStorage, "ais_sid");
    const site = location.hostname;

    let buffer = [];
    let sending = false;

    const FLUSH_INTERVAL = 1000;
    const MAX_BATCH = 5;
    const SCROLL_STEP = isSamsung ? 5 : 2;

    let lastScrollPercent = 0;
    let lastReportedStep = 0;

    function push(et, p) {
        buffer.push({
            et,
            ts: Date.now(),
            p
        });

        if (buffer.length >= MAX_BATCH) {
            flush();
        }
    }

    function flush() {
        if (!buffer.length || sending) return;

        sending = true;

        const payload = {
            site,
            uid,
            sid,
            ua,
            ev: buffer
        };

        buffer = [];

        fetch(EP, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload),
            keepalive: !isSamsung
        })
        .catch(() => {})
        .finally(() => {
            sending = false;
        });
    }

    setInterval(flush, FLUSH_INTERVAL);

    document.addEventListener("click", function (e) {
        const el = e.target.closest("button, input[type=submit], .t-btn, .t-submit");
        if (!el) return;

        push("click", {
            button_text: (el.innerText || el.value || "").trim() || null,
            id: el.id || null,
            cls: el.className || null
        });

        flush();
    }, true);

    document.addEventListener("scroll", function () {
        const doc = document.documentElement;
        const maxScroll = doc.scrollHeight - window.innerHeight;
        if (maxScroll <= 0) return;

        const current = Math.round((window.scrollY / maxScroll) * 100);
        const step = Math.floor(current / SCROLL_STEP) * SCROLL_STEP;

        if (step === lastReportedStep) return;

        const direction = current > lastScrollPercent ? "down" : "up";

        lastScrollPercent = current;
        lastReportedStep = step;

        push("hb", {
            sp: current,
            dir: direction
        });
    }, { passive: true });

})();
</script>
