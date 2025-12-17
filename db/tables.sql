-- USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    telegram_id TEXT,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT,
    auth_method TEXT,
    category TEXT,
    dashboard_token TEXT,
    dashboard_token_created_at TIMESTAMPTZ
);

-- PLANS
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    price INT,
    sites_limit INT,
    events_limit INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- USER PLANS
CREATE TABLE IF NOT EXISTS user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan_id UUID REFERENCES plans(id),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SITES
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    site_url TEXT NOT NULL,
    api_key TEXT,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_scan_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- SITE STRUCTURE
CREATE TABLE IF NOT EXISTS site_structure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id),
    url TEXT,
    tilda_id TEXT,
    element_type TEXT,
    text_current TEXT,
    position_index INT,
    is_active BOOLEAN DEFAULT TRUE,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

------------------------------------------------------------
--                EVENTS (ACTUAL SDK VERSION)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- BASIC
    site_url TEXT NOT NULL,
    uid TEXT,
    session_id TEXT,
    event_type TEXT NOT NULL,                 -- 'scroll', 'click'
    event_time TIMESTAMPTZ NOT NULL,          -- client timestamp
    received_at TIMESTAMPTZ DEFAULT NOW(),    -- server timestamp

    --------------------------------------------------------
    -- SCROLL EVENT
    --------------------------------------------------------
    scroll_position_percent INT,

    --------------------------------------------------------
    -- CLICK EVENT
    --------------------------------------------------------
    button_text TEXT,
    button_id TEXT,
    button_class TEXT,

    --------------------------------------------------------
    -- DEVICE META
    --------------------------------------------------------
    device_type TEXT,
    os TEXT,
    browser TEXT,
    user_agent TEXT,

    --------------------------------------------------------
    -- NETWORK
    --------------------------------------------------------
    client_ip INET
);

------------------------------------------------------------
--              SESSION_SUMMARY (AGGREGATED VISITS)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    --------------------------------------------------------
    -- IDENTIFIERS
    --------------------------------------------------------
    site_url TEXT NOT NULL,
    uid TEXT,
    session_id TEXT NOT NULL,     -- session id из SDK (одна строка = один визит)

    --------------------------------------------------------
    -- VISIT TIME
    --------------------------------------------------------
    visit_start TIMESTAMPTZ NOT NULL,
    visit_end TIMESTAMPTZ NOT NULL,
    duration_seconds INT NOT NULL,

    --------------------------------------------------------
    -- GEO (by IP)
    --------------------------------------------------------
    country TEXT,
    city TEXT,

    --------------------------------------------------------
    -- DEVICE (parsed user-agent)
    --------------------------------------------------------
    device_type TEXT,             -- mobile / desktop
    os TEXT,
    browser TEXT,

    --------------------------------------------------------
    -- SCROLL SUMMARY
    --------------------------------------------------------
    max_scroll_depth INT,
    final_scroll_depth INT,

    -- [{ t: ms_from_start, depth: %, stop_ms: ms }]
    scroll_stops JSONB,

    --------------------------------------------------------
    -- CLICKS SUMMARY
    --------------------------------------------------------
    -- [{ t: ms_from_start, button: text }]
    click_buttons JSONB,

    --------------------------------------------------------
    -- AGGREGATES
    --------------------------------------------------------
    total_scroll_events INT,
    total_click_events INT,

    --------------------------------------------------------
    -- META
    --------------------------------------------------------
    created_at TIMESTAMPTZ DEFAULT NOW()
);


------------------------------------------------------------
--        APP / DASHBOARD READ MODEL (OWNER → SITE → VISITS)
------------------------------------------------------------
CREATE OR REPLACE VIEW dashboard_session_summary AS
SELECT
    -- owner
    u.id                AS owner_user_id,
    u.email             AS owner_email,
    u.dashboard_token   AS dashboard_token,

    -- site
    s.id                AS site_id,
    s.site_url          AS site_url,
    s.category          AS site_category,
    s.is_active         AS site_is_active,

    -- visit
    ss.id               AS session_summary_id,
    ss.session_id,
    ss.uid              AS visitor_uid,

    ss.visit_start,
    ss.visit_end,
    ss.duration_seconds,

    -- geo
    ss.country,
    ss.city,

    -- device
    ss.device_type,
    ss.os,
    ss.browser,

    -- scroll
    ss.max_scroll_depth,
    ss.final_scroll_depth,
    ss.scroll_stops,

    -- clicks
    ss.click_buttons,
    ss.total_scroll_events,
    ss.total_click_events,

    ss.created_at
FROM session_summary ss
JOIN sites s
  ON s.site_url = ss.site_url
JOIN users u
  ON u.id = s.user_id;
