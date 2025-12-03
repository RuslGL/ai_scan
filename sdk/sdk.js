(function () {
    const BATCH_SIZE = 20;
    const BATCH_INTERVAL = 2000;
    const HEARTBEAT_INTERVAL = 15000;
    const SESSION_TIMEOUT_MS = 1800000;

    const UID_KEY = "ai_scan_uid";
    const SESSION_KEY = "ai_scan_session";
    const OFFLINE_QUEUE_KEY = "ai_scan_offline_queue";

    const siteId = location.hostname;
    const apiUrl = "https://ai-scan.tech/track";

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

        enqueueEvent(
            buildEvent("session_start", {
                session_id: sessionId,
                session_start_ts: sessionStartTs,
            })
        );
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

    function getPageMeta() {
        const doc = document.documentElement;
        const body = document.body;
        const scrollTop =
            window.scrollY || doc.scrollTop || body.scrollTop || 0;
        const scrollHeight = Math.max(
            body.scrollHeight,
            doc.scrollHeight,
            body.offsetHeight,
            doc.offsetHeight,
            body.clientHeight,
            doc.clientHeight
        );
        const viewportHeight =
            window.innerHeight ||
            doc.clientHeight ||
            body.clientHeight ||
            1;
        const maxScrollable = Math.max(scrollHeight - viewportHeight, 1);
        const scrollPercent = Math.min(
            100,
            Math.max(0, Math.round((scrollTop / maxScrollable) * 100))
        );

        return {
            page_url: location.href,
            page_title: document.title || null,
            referrer: document.referrer || null,
            user_agent: navigator.userAgent || null,
            language: navigator.language || null,
            viewport_width: window.innerWidth || null,
            viewport_height: window.innerHeight || null,
            screen_width:
                (window.screen && window.screen.width) || null,
            screen_height:
                (window.screen && window.screen.height) || null,
            scroll_y: scrollTop,
            scroll_percent: scrollPercent,
        };
    }

    function calcScrollPercent() {
        const doc = document.documentElement;
        const body = document.body;
        const scrollTop =
            window.scrollY || doc.scrollTop || body.scrollTop || 0;
        const scrollHeight = Math.max(
            body.scrollHeight,
            doc.scrollHeight,
            body.offsetHeight,
            doc.offsetHeight,
            body.clientHeight,
            doc.clientHeight
        );
        const viewportHeight =
            window.innerHeight ||
            doc.clientHeight ||
            body.clientHeight ||
            1;
        const maxScrollable = Math.max(scrollHeight - viewportHeight, 1);
        return Math.min(
            100,
            Math.max(0, Math.round((scrollTop / maxScrollable) * 100))
        );
    }

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
            payloadEvents = payloadEvents.concat(
                queue.splice(0, need)
            );
        }

        if (payloadEvents.length === 0) return;

        const body = JSON.stringify({
            site_id: siteId,
            uid: uid,
            session_id: sessionId,
            events: payloadEvents,
        });

        fetch(apiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
        })
            .then((res) => {
                if (!res.ok) {
                    offlineQueue = payloadEvents.concat(offlineQueue);
                    saveOfflineQueue();
                } else {
                    saveOfflineQueue();
                }
            })
            .catch(() => {
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

    function buildEvent(event_type, payload) {
        return {
            event_id: generateId(),
            event_type,
            ts: Date.now(),
            site_id: siteId,
            uid: uid,
            session_id: sessionId,
            meta: getPageMeta(),
            payload: payload || {},
        };
    }

    function track(event_type, payload) {
        markActivity();
        enqueueEvent(buildEvent(event_type, payload));
    }

    document.addEventListener(
        "click",
        function (e) {
            const target = e.target;
            if (!target) return;

            const info = extractElementInfo(target);
            track("click", {
                tag: info.tag,
                id: info.id,
                class_name: info.className,
                text: info.text,
                selector: info.selector,
                block_title: info.blockTitle,
                section_name: info.sectionName,
                x: e.clientX,
                y: e.clientY,
            });
        },
        true
    );

    function extractElementInfo(el) {
        const tag = (el.tagName || "").toLowerCase();
        const id = el.id || null;
        const className = (el.className || "").toString();
        const text = (el.innerText || el.textContent || "")
            .trim()
            .slice(0, 120);

        const selector = buildSelector(el);
        const blockTitle = findNearestTitle(el);
        const sectionName = findSectionName(el);

        return { tag, id, className, text, selector, blockTitle, sectionName };
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
            } else {
                if (el.className) {
                    const cls = el.className
                        .trim()
                        .split(/\s+/)
                        .filter(Boolean)
                        .join(".");
                    if (cls) selector += "." + cls;
                }
                const parent = el.parentElement;
                if (parent) {
                    const siblings = Array.from(parent.children).filter(
                        (c) => c.tagName === el.tagName
                    );
                    if (siblings.length > 1) {
                        const idx = siblings.indexOf(el);
                        selector += `:nth-of-type(${idx + 1})`;
                    }
                }
            }
            path.unshift(selector);
            el = el.parentElement;
        }
        return path.join(" > ");
    }

    function findNearestTitle(el) {
        let node = el;
        while (node && node !== document.body) {
            const h =
                node.querySelector &&
                node.querySelector("h1,h2,h3,h4");
            if (h && (h.innerText || h.textContent)) {
                return (h.innerText || h.textContent)
                    .trim()
                    .slice(0, 120);
            }
            node = node.parentElement;
        }
        return null;
    }

    function findSectionName(el) {
        let node = el;
        while (node && node !== document.body) {
            if (node.getAttribute) {
                const ds =
                    node.getAttribute("data-section-name") ||
                    node.getAttribute("aria-label");
                if (ds) return ds.slice(0, 120);
            }
            node = node.parentElement;
        }
        return null;
    }

    let maxScrollPercent = calcScrollPercent();
    let lastScrollMilestone = 0;
    let scrollTimeout = null;

    window.addEventListener(
        "scroll",
        function () {
            if (scrollTimeout) return;
            scrollTimeout = setTimeout(function () {
                scrollTimeout = null;
                const p = calcScrollPercent();
                if (p > maxScrollPercent) maxScrollPercent = p;

                const milestone = Math.floor(p / 10) * 10;
                if (milestone >= 10 && milestone > lastScrollMilestone) {
                    lastScrollMilestone = milestone;
                    track("scroll_depth", {
                        current_percent: p,
                        max_percent: maxScrollPercent,
                        milestone: milestone,
                    });
                }
            }, 250);
        },
        { passive: true }
    );

    let sessionStartMs = Date.now();

    ["click", "scroll", "keydown", "mousemove", "touchstart"].forEach((ev) => {
        window.addEventListener(ev, markActivity, { passive: true });
    });

    setInterval(function () {
        const now = Date.now();
        const sessionDuration = now - sessionStartMs;
        const sinceLastActivity = now - (lastActivityTs || sessionStartMs);
        track("heartbeat", {
            session_duration_ms: sessionDuration,
            since_last_activity_ms: sinceLastActivity,
            max_scroll_percent: maxScrollPercent,
        });
    }, HEARTBEAT_INTERVAL);

    function initFormsTracking() {
        const forms = document.querySelectorAll("form");
        forms.forEach((form, index) => {
            const formId =
                form.id ||
                form.getAttribute("name") ||
                `form_${index}`;
            const meta = extractFormMeta(form, formId);

            track("form_view", meta);

            let started = false;
            form.addEventListener("focusin", function () {
                if (!started) {
                    started = true;
                    track("form_start", meta);
                }
            });

            form.addEventListener("submit", function () {
                const structure = extractFormStructure(form);
                track(
                    "form_submit",
                    Object.assign({}, meta, {
                        fields: structure,
                    })
                );
            });
        });
    }

    function extractFormMeta(form, formId) {
        const submitBtn = form.querySelector(
            "button[type=submit], input[type=submit]"
        );
        const btnText =
            submitBtn &&
            (submitBtn.innerText ||
                submitBtn.value ||
                "")
                .trim()
                .slice(0, 120) ||
            null;
        const title = findNearestTitle(form);
        const selector = buildSelector(form);
        return {
            form_id: formId,
            form_selector: selector,
            form_title: title,
            submit_text: btnText,
        };
    }

    function extractFormStructure(form) {
        const fields = [];
        const elements = form.querySelectorAll(
            "input, select, textarea"
        );
        elements.forEach((el) => {
            const tag = (el.tagName || "").toLowerCase();
            const type =
                (el.getAttribute("type") || "").toLowerCase() ||
                (tag === "textarea"
                    ? "textarea"
                    : tag === "select"
                    ? "select"
                    : "text");
            fields.push({
                name: el.name || null,
                tag: tag,
                type: type,
                required: !!el.required,
            });
        });
        return fields;
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initFormsTracking);
    } else {
        initFormsTracking();
    }

    track("page_view", {
        entry_scroll_percent: calcScrollPercent(),
    });

    function sendPageExit(reason) {
        track("page_exit", {
            reason: reason || "unload",
            final_scroll_percent: calcScrollPercent(),
            max_scroll_percent: maxScrollPercent,
            session_duration_ms: Date.now() - sessionStartMs,
        });
        flushQueue();
    }

    window.addEventListener("beforeunload", function () {
        sendPageExit("beforeunload");
    });

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") {
            sendPageExit("hidden");
        }
    });

    window.aiScan = {
        uid: uid,
        session_id: sessionId,
        track: function (event_type, payload) {
            track(event_type, payload || {});
        },
    };
})();
