(function () {
    const BATCH_SIZE = 20;
    const BATCH_INTERVAL = 2000;
    const HEARTBEAT_INTERVAL = 15000;
    const SESSION_TIMEOUT_MS = 1800000;

    const UID_KEY = "ai_scan_uid";
    const SESSION_KEY = "ai_scan_session";
    const OFFLINE_QUEUE_KEY = "ai_scan_offline_queue";

    const siteUrl = location.hostname;
    const apiUrl = "https://ai-scan.tech/track";

    // ---------------------------
    //   ID / UID / SESSION
    // ---------------------------
    function generateId() {
        return (
            Math.random().toString(36).slice(2) +
            "-" +
            Date.now().toString(36) +
            "-" +
            Math.random().toString(36).slice(2)
        );
    }

    function getUID() {
        try {
            let uid = localStorage.getItem(UID_KEY);
            if (!uid) {
                uid = generateId();
                localStorage.setItem(UID_KEY, uid);
            }
            return uid;
        } catch (e) {
            return generateId();
        }
    }

    const uid = getUID();

    let sessionId, sessionStartTs, lastActivityTs;

    function loadOrCreateSession() {
        const now = Date.now();
        let raw = null;
        try {
            raw = localStorage.getItem(SESSION_KEY);
        } catch (e) {}

        if (raw) {
            try {
                const data = JSON.parse(raw);
                if (now - data.lastActivity < SESSION_TIMEOUT_MS) {
                    sessionId = data.id;
                    sessionStartTs = data.start;
                    lastActivityTs = data.lastActivity;
                    return;
                }
            } catch (e) {}
        }

        sessionId = generateId();
        sessionStartTs = now;
        lastActivityTs = now;
        persistSession();

        // фиксируем старт сессии
        enqueueEvent(buildEvent("session_start", {}));
    }

    function persistSession() {
        const now = Date.now();
        try {
            localStorage.setItem(
                SESSION_KEY,
                JSON.stringify({
                    id: sessionId,
                    start: sessionStartTs,
                    lastActivity: lastActivityTs || now,
                })
            );
        } catch (e) {}
    }

    function markActivity() {
        lastActivityTs = Date.now();
        persistSession();
    }

    loadOrCreateSession();

    // ---------------------------
    //   DEVICE / BROWSER META
    // ---------------------------
    function getDeviceInfo() {
        const ua = (navigator.userAgent || "").toLowerCase();

        let device_type = "desktop";
        if (/mobile|iphone|ipod|android.*mobile/.test(ua)) {
            device_type = "mobile";
        } else if (/ipad|tablet/.test(ua)) {
            device_type = "tablet";
        }

        let os = "Other";
        if (ua.includes("windows")) os = "Windows";
        else if (ua.includes("mac os x") || ua.includes("macintosh")) os = "macOS";
        else if (ua.includes("android")) os = "Android";
        else if (ua.includes("iphone") || ua.includes("ipad") || ua.includes("ipod")) os = "iOS";
        else if (ua.includes("linux")) os = "Linux";

        let browser = "Other";
        if (ua.includes("edg/")) browser = "Edge";
        else if (ua.includes("opr/") || ua.includes("opera")) browser = "Opera";
        else if (ua.includes("chrome") && !ua.includes("edg/") && !ua.includes("opr/"))
            browser = "Chrome";
        else if (ua.includes("safari") && !ua.includes("chrome") && !ua.includes("chromium"))
            browser = "Safari";
        else if (ua.includes("firefox")) browser = "Firefox";

        const vw = window.innerWidth || null;
        const vh = window.innerHeight || null;
        const sw = (window.screen && window.screen.width) || null;
        const sh = (window.screen && window.screen.height) || null;

        return {
            device_type: device_type,
            os: os,
            browser: browser,
            user_agent: navigator.userAgent || null,
            viewport_width: vw,
            viewport_height: vh,
            screen_width: sw,
            screen_height: sh,
        };
    }

    // ------------------------
    //   SCROLL PERCENT (Safari ok)
    // ------------------------
    function calcScrollPercent() {
        try {
            const el = document.scrollingElement || document.documentElement;

            const scrollTop =
                window.pageYOffset ||
                el.scrollTop ||
                0;

            const scrollHeight = el.scrollHeight || 0;
            const clientHeight = el.clientHeight || window.innerHeight || 1;

            const maxScrollable = Math.max(scrollHeight - clientHeight, 1);

            return Math.min(
                100,
                Math.max(0, Math.round((scrollTop / maxScrollable) * 100))
            );
        } catch (e) {
            return 0;
        }
    }

    function getScrollY() {
        const el = document.scrollingElement || document.documentElement;
        return (
            window.pageYOffset ||
            el.scrollTop ||
            0
        );
    }

    // ---------------------------
    //   QUEUE / OFFLINE QUEUE
    // ---------------------------
    const queue = [];
    let offlineQueue = loadOfflineQueue();

    function loadOfflineQueue() {
        try {
            const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
            if (!raw) return [];
            const arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr : [];
        } catch (e) {
            return [];
        }
    }

    function saveOfflineQueue() {
        try {
            localStorage.setItem(
                OFFLINE_QUEUE_KEY,
                JSON.stringify(offlineQueue.slice(0, 2000))
            );
        } catch (e) {}
    }

    function enqueueEvent(event) {
        queue.push(event);
    }

    function flushQueue() {
        if (!navigator.onLine) {
            offlineQueue = offlineQueue.concat(queue);
            queue.length = 0;
            saveOfflineQueue();
            return;
        }

        let payloadEvents = [];

        if (offlineQueue.length > 0) {
            payloadEvents = payloadEvents.concat(
                offlineQueue.splice(0, BATCH_SIZE)
            );
        }

        if (queue.length > 0 && payloadEvents.length < BATCH_SIZE) {
            const need = BATCH_SIZE - payloadEvents.length;
            payloadEvents = payloadEvents.concat(queue.splice(0, need));
        }

        if (payloadEvents.length === 0) return;

        fetch(apiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                site_url: siteUrl,
                uid: uid,
                session_id: sessionId,
                events: payloadEvents,
            }),
        }).catch(() => {
            offlineQueue = payloadEvents.concat(offlineQueue);
            saveOfflineQueue();
        });
    }

    setInterval(flushQueue, BATCH_INTERVAL);

    window.addEventListener("beforeunload", function () {
        if (queue.length > 0) {
            offlineQueue = offlineQueue.concat(queue);
            queue.length = 0;
            saveOfflineQueue();
        }
    });

    // ---------------------------
    //   BUILD EVENT / TRACK
    // ---------------------------
    function buildEvent(event_type, payload) {
        return {
            event_id: generateId(),
            event_type: event_type,
            ts: Date.now(),
            site_url: siteUrl,
            uid: uid,
            session_id: sessionId,
            payload: Object.assign({}, payload || {}, {
                device: getDeviceInfo(),
            }),
        };
    }

    function track(event_type, payload) {
        markActivity();
        enqueueEvent(buildEvent(event_type, payload));
    }

    // ------------------------------
    //      CLICK ONLY ON BUTTONS
    // ------------------------------
    function isButton(el) {
        if (!el) return false;

        const tag = el.tagName ? el.tagName.toLowerCase() : "";
        if (tag === "button") return true;

        if (tag === "input") {
            const type = (el.type || "").toLowerCase();
            if (type === "button" || type === "submit") return true;
        }

        const cls = (el.className || "").toString().toLowerCase();
        if (
            cls.includes("btn") ||
            cls.includes("button") ||
            cls.includes("t-btn")
        ) {
            return true;
        }

        return false;
    }

    function buildSelector(el) {
        if (!el) return null;
        const path = [];

        while (el && el.nodeType === 1 && el !== document.body) {
            let selector = el.tagName.toLowerCase();

            if (el.id) {
                selector += "#" + el.id;
                path.unshift(selector);
                break;
            }

            if (el.className) {
                const cls = el.className
                    .toString()
                    .trim()
                    .split(/\s+/)
                    .filter(Boolean)
                    .join(".");
                if (cls) selector += "." + cls;
            }

            const parent = el.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(function (x) {
                    return x.tagName === el.tagName;
                });
                if (siblings.length > 1) {
                    selector += ":nth-of-type(" + (siblings.indexOf(el) + 1) + ")";
                }
            }

            path.unshift(selector);
            el = el.parentElement;
        }

        return path.join(" > ");
    }

    document.addEventListener(
        "click",
        function (e) {
            const t = e.target;
            if (!isButton(t)) return;

            const rawText =
                (t.innerText || t.textContent || "").trim().slice(0, 80);

            var eventName = rawText
                .replace(/\s+/g, "_")
                .replace(/[^a-zA-Z0-9А-Яа-я_]/g, "")
                .slice(0, 40);

            if (!eventName) eventName = "button";

            const event_type = "click_button:" + eventName;

            track(event_type, {
                id: t.id || null,
                class_name: t.className || null,
                text: rawText,
                selector: buildSelector(t)
            });
        },
        true
    );

    // ------------------------------
    //      FORM SUBMIT SUCCESS
    // ------------------------------
    function extractFormStructure(form) {
        const fields = [];
        const els = form.querySelectorAll("input, textarea, select");

        els.forEach(function (el) {
            fields.push({
                name: el.name || null,
                type: (el.type || el.tagName || "").toLowerCase(),
                required: !!el.required,
            });
        });

        return fields;
    }

    function getSubmitButtonText(form) {
        const btn = form.querySelector("button[type=submit], input[type=submit]");
        if (!btn) return null;
        return (btn.innerText || btn.value || "")
            .trim()
            .slice(0, 80);
    }

    document.addEventListener(
        "submit",
        function (e) {
            const form = e.target;
            if (!form || form.nodeName !== "FORM") return;

            const fields = extractFormStructure(form);
            const btnText = getSubmitButtonText(form) || "";

            var slug = btnText
                .replace(/\s+/g, "_")
                .replace(/[^a-zA-Z0-9А-Яа-я_]/g, "")
                .slice(0, 40);

            if (!slug) slug = "submit";

            const event_type = "form_submit_success:" + slug;

            track(event_type, {
                form_selector: buildSelector(form),
                fields: fields,
                button_text: btnText || null,
            });
        },
        true
    );

    // ---------------------------
    //      HEARTBEAT + SCROLL
    // ---------------------------
    let sessionStartMs = Date.now();
    let maxScrollPercent = 0;

    setInterval(function () {
        const now = Date.now();
        const currentPercent = calcScrollPercent();
        if (currentPercent > maxScrollPercent) maxScrollPercent = currentPercent;

        const scrollY = getScrollY();

        track("heartbeat", {
            session_duration_ms: now - sessionStartMs,
            since_last_activity_ms: now - (lastActivityTs || sessionStartMs),
            scroll_percent: currentPercent,
            max_scroll_percent: maxScrollPercent,
            scroll_y: scrollY,
        });
    }, HEARTBEAT_INTERVAL);

    // ---------------------------
    //      PAGE VIEW
    // ---------------------------
    track("page_view", {
        entry_scroll_percent: calcScrollPercent(),
    });

    // ---------------------------
    //      PUBLIC API
    // ---------------------------
    window.aiScan = {
        uid: uid,
        session_id: sessionId,
        track: track,
    };
})();
